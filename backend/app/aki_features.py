"""Pure, cutoff-safe feature and label construction for synthetic AKI research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence

import pandas as pd

from .clinical_rules import calculate_creatinine_rule
from .patients import ClinicalContext, PatientDetail
from .synthetic_data import EhrEvent, IotObservation


@dataclass(frozen=True)
class FeatureSchema:
    version: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class FreshnessPolicy:
    version: str
    maximum_age: timedelta


@dataclass(frozen=True)
class PredictionSnapshot:
    status: str
    reason: str | None
    frame: pd.DataFrame | None
    ehr_evidence: tuple[EhrEvent, ...]
    iot_evidence: tuple[IotObservation, ...]


@dataclass(frozen=True)
class TrainingRows:
    """Feature rows with labels and grouping data kept outside the model frame."""

    features: pd.DataFrame
    labels: tuple[int, ...]
    patient_groups: tuple[str, ...]
    cutoffs: tuple[datetime, ...]


FEATURE_SCHEMA = FeatureSchema(
    "aki-combined-2026.10.04",
    (
        "age_years",
        "latest_creatinine_mg_dl",
        "creatinine_delta_48h_mg_dl",
        "latest_systolic_bp_mmhg",
    ),
)
FRESHNESS_POLICY = FreshnessPolicy("required-observation-24h-2026.10.04", timedelta(hours=24))
LABEL_VERSION = "new-aki-24h-2026.10.04"

_EHR_SOURCE = "twinbean-synthetic-ehr"
_IOT_SOURCE = "twinbean-simulated-iot"
_FORBIDDEN_FIELDS = frozenset(
    {
        "patient_id",
        "cohort_id",
        "scenario",
        "outcome",
        "label",
        "future_value",
        "clinical_rule",
        "clinical_rule_result",
        "prediction",
        "risk",
    }
)


def build_prediction_snapshot(context: ClinicalContext, cutoff: datetime) -> PredictionSnapshot:
    """Validate one request-time snapshot before pandas or model work begins."""

    if not _is_utc(cutoff):
        return _unavailable("invalid_cutoff")
    integrity_error = _validate_context(context, cutoff)
    if integrity_error:
        return _unavailable(integrity_error)

    patient = context.patient.patient
    creatinine_events = [
        event
        for event in context.patient.ehr_history
        if event.event_type == "laboratory" and event.data.get("test_name") == "creatinine"
    ]
    for event in creatinine_events:
        error = _validate_creatinine(event)
        if error:
            return _unavailable(error)
    if len(creatinine_events) < 2:
        return _unavailable("missing_creatinine_history")
    creatinine_events.sort(key=lambda event: (event.event_time, event.event_id))
    latest = creatinine_events[-1]
    prior = [
        event
        for event in creatinine_events[:-1]
        if latest.event_time - timedelta(hours=48) <= event.event_time < latest.event_time
    ]
    if not prior:
        return _unavailable("missing_creatinine_comparator")
    comparator = prior[-1]
    freshness_error = _check_freshness(latest.event_time, cutoff, "ehr") or _check_freshness(
        comparator.event_time, cutoff, "ehr"
    )
    if freshness_error:
        return _unavailable(freshness_error)

    blood_pressures = [
        observation
        for observation in context.patient.iot_observations
        if observation.measurement_type == "blood_pressure"
    ]
    for observation in blood_pressures:
        error = _validate_blood_pressure(observation)
        if error:
            return _unavailable(error)
    if not blood_pressures:
        return _unavailable("missing_iot_observation")
    blood_pressures.sort(key=lambda observation: (observation.observed_at, observation.observation_id))
    latest_bp = blood_pressures[-1]
    freshness_error = _check_freshness(latest_bp.observed_at, cutoff, "iot")
    if freshness_error:
        return _unavailable(freshness_error)

    latest_value = float(latest.data["value"])
    comparator_value = float(comparator.data["value"])
    row = {
        "age_years": float(patient.age),
        "latest_creatinine_mg_dl": latest_value,
        "creatinine_delta_48h_mg_dl": latest_value - comparator_value,
        "latest_systolic_bp_mmhg": float(latest_bp.data["systolic"]),
    }
    frame = pd.DataFrame([row], columns=list(FEATURE_SCHEMA.columns))
    return PredictionSnapshot("available", None, frame, (comparator, latest), (latest_bp,))


def build_training_rows(contexts: Sequence[ClinicalContext], cutoffs: Sequence[datetime]) -> TrainingRows:
    """Build explicit cutoff-safe rows and strict new-AKI labels for training only."""

    if len(contexts) != len(cutoffs):
        raise ValueError("contexts and cutoffs must have equal length")
    frames: list[pd.DataFrame] = []
    labels: list[int] = []
    groups: list[str] = []
    validated_cutoffs: list[datetime] = []
    for context, cutoff in zip(contexts, cutoffs, strict=True):
        if not _is_utc(cutoff):
            raise ValueError("training cutoff must be timezone-aware UTC")
        integrity_error = _validate_context(context, None)
        if integrity_error:
            raise ValueError(f"training context unavailable: {integrity_error}")
        for event in context.patient.ehr_history:
            if event.event_type == "laboratory" and event.data.get("test_name") == "creatinine":
                feature_error = _validate_creatinine(event)
                if feature_error:
                    raise ValueError(f"training context unavailable: {feature_error}")
        past_context = _with_histories(
            context,
            tuple(event for event in context.patient.ehr_history if event.event_time <= cutoff),
            tuple(observation for observation in context.patient.iot_observations if observation.observed_at <= cutoff),
        )
        snapshot = build_prediction_snapshot(past_context, cutoff)
        if snapshot.status != "available" or snapshot.frame is None:
            raise ValueError(f"training snapshot unavailable: {snapshot.reason}")
        frames.append(snapshot.frame)
        labels.append(_new_aki_label(context.patient.ehr_history, cutoff))
        groups.append(context.patient.patient.patient_id)
        validated_cutoffs.append(cutoff)
    return TrainingRows(
        pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(FEATURE_SCHEMA.columns)),
        tuple(labels),
        tuple(groups),
        tuple(validated_cutoffs),
    )


def _unavailable(reason: str) -> PredictionSnapshot:
    return PredictionSnapshot("unavailable", reason, None, (), ())


def _is_utc(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() == UTC.utcoffset(None)


def _validate_context(context: ClinicalContext, cutoff: datetime | None) -> str | None:
    if not isinstance(context, ClinicalContext) or not context.cohort_id.startswith("cohort-"):
        return "invalid_cohort_context"
    if len(context.manifest_checksum) != 64 or any(character not in "0123456789abcdef" for character in context.manifest_checksum):
        return "invalid_cohort_context"
    patient = context.patient.patient
    if not isinstance(patient.age, int) or isinstance(patient.age, bool) or patient.age < 18:
        return "invalid_patient"
    for event in context.patient.ehr_history:
        error = _validate_ehr_record(event, context, patient.patient_id, cutoff)
        if error:
            return error
    for observation in context.patient.iot_observations:
        error = _validate_iot_record(observation, context, patient.patient_id, cutoff)
        if error:
            return error
    return None


def _validate_ehr_record(event: EhrEvent, context: ClinicalContext, patient_id: str, cutoff: datetime | None) -> str | None:
    if not _is_utc(event.event_time):
        return "invalid_ehr_timestamp"
    if cutoff is not None and event.event_time > cutoff:
        return "future_observation"
    if event.synthetic is not True or event.source != _EHR_SOURCE or event.generator_version != context.generator_version or event.seed != context.seed:
        return "invalid_ehr_provenance"
    if event.patient_id != patient_id:
        return "invalid_ehr_ownership"
    if not isinstance(event.data, Mapping):
        return "invalid_ehr_schema"
    return None


def _validate_iot_record(observation: IotObservation, context: ClinicalContext, patient_id: str, cutoff: datetime | None) -> str | None:
    if not _is_utc(observation.observed_at):
        return "invalid_iot_timestamp"
    if cutoff is not None and observation.observed_at > cutoff:
        return "future_observation"
    if observation.synthetic is not True or observation.source != _IOT_SOURCE or observation.generator_version != context.generator_version or observation.seed != context.seed:
        return "invalid_iot_provenance"
    if observation.patient_id != patient_id:
        return "invalid_iot_ownership"
    if not isinstance(observation.data, Mapping):
        return "invalid_iot_schema"
    return None


def _validate_creatinine(event: EhrEvent) -> str | None:
    data = event.data
    if _FORBIDDEN_FIELDS & set(data):
        return "forbidden_ehr_field"
    if set(data) != {"test_name", "value", "unit"}:
        return "invalid_ehr_schema"
    if data.get("unit") != "mg/dL":
        return "invalid_ehr_unit"
    if not _valid_number(data.get("value")):
        return "invalid_ehr_value"
    return None


def _validate_blood_pressure(observation: IotObservation) -> str | None:
    data = observation.data
    if _FORBIDDEN_FIELDS & set(data):
        return "forbidden_iot_field"
    if set(data) != {"systolic", "diastolic", "unit"}:
        return "invalid_iot_schema"
    if data.get("unit") != "mmHg":
        return "invalid_iot_unit"
    if not _valid_number(data.get("systolic")) or not _valid_number(data.get("diastolic")):
        return "invalid_iot_value"
    return None


def _valid_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _check_freshness(observed_at: datetime, cutoff: datetime, stream: str) -> str | None:
    if cutoff - observed_at > FRESHNESS_POLICY.maximum_age:
        return f"stale_{stream}_observation"
    return None


def _with_histories(context: ClinicalContext, events: tuple[EhrEvent, ...], observations: tuple[IotObservation, ...]) -> ClinicalContext:
    detail = PatientDetail(patient=context.patient.patient, ehr_history=list(events), iot_observations=list(observations))
    return ClinicalContext(context.cohort_id, context.manifest_checksum, context.generator_version, context.seed, detail)


def _new_aki_label(events: Sequence[EhrEvent], cutoff: datetime) -> int:
    current = calculate_creatinine_rule(events, cutoff)
    if current.status == "criteria_met":
        return 0
    horizon = cutoff + timedelta(hours=24)
    candidates = sorted(
        (event for event in events if cutoff < event.event_time <= horizon),
        key=lambda event: (event.event_time, event.event_id),
    )
    return int(any(calculate_creatinine_rule(events, event.event_time).status == "criteria_met" for event in candidates))
