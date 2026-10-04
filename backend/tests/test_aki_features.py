from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.aki_features import FEATURE_SCHEMA, FRESHNESS_POLICY, build_prediction_snapshot, build_training_rows
from app.patients import ClinicalContext, PatientDetail, PatientSummary
from app.synthetic_data import EhrEvent, IotObservation


CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
PATIENT_ID = "tbp-feature-patient"
GENERATOR_VERSION = "feature-contract-v1"
SEED = 77


def _event(hours: float, value: object, unit: object = "mg/dL", **data: object) -> EhrEvent:
    return EhrEvent(
        event_id=f"ehr-{hours}", patient_id=PATIENT_ID, event_type="laboratory",
        event_time=CUTOFF - timedelta(hours=hours),
        data={"test_name": "creatinine", "value": value, "unit": unit, **data},
        synthetic=True, generator_version=GENERATOR_VERSION, seed=SEED, source="twinbean-synthetic-ehr",
    )


def _observation(hours: float, systolic: object = 130, unit: object = "mmHg", **data: object) -> IotObservation:
    return IotObservation(
        observation_id=f"iot-{hours}", patient_id=PATIENT_ID, measurement_type="blood_pressure",
        observed_at=CUTOFF - timedelta(hours=hours),
        data={"systolic": systolic, "diastolic": 80, "unit": unit, **data},
        synthetic=True, generator_version=GENERATOR_VERSION, seed=SEED, source="twinbean-simulated-iot",
    )


def _context(events: tuple[EhrEvent, ...] | None = None, observations: tuple[IotObservation, ...] | None = None) -> ClinicalContext:
    return ClinicalContext(
        cohort_id="cohort-feature-contract", manifest_checksum="a" * 64,
        generator_version=GENERATOR_VERSION, seed=SEED,
        patient=PatientDetail(
            patient=PatientSummary(patient_id=PATIENT_ID, display_name="Synthetic Feature Patient", age=61, ckd_stage="G3b"),
            ehr_history=list(events or (_event(20, 1.1), _event(0, 1.2))),
            iot_observations=list(observations or (_observation(0),)),
        ),
    )


def test_valid_snapshot_is_an_exact_ordered_combined_stream_frame() -> None:
    snapshot = build_prediction_snapshot(_context(), CUTOFF)

    assert snapshot.status == "available"
    assert FEATURE_SCHEMA.version == "aki-combined-2026.10.04"
    assert FEATURE_SCHEMA.columns == (
        "age_years", "latest_creatinine_mg_dl", "creatinine_delta_48h_mg_dl", "latest_systolic_bp_mmhg",
    )
    assert FRESHNESS_POLICY.version == "required-observation-24h-2026.10.04"
    assert tuple(snapshot.frame.columns) == FEATURE_SCHEMA.columns
    assert snapshot.frame.iloc[0].to_dict() == {
        "age_years": 61.0, "latest_creatinine_mg_dl": 1.2,
        "creatinine_delta_48h_mg_dl": pytest.approx(0.1), "latest_systolic_bp_mmhg": 130.0,
    }
    assert [event.event_id for event in snapshot.ehr_evidence] == ["ehr-20", "ehr-0"]
    assert [item.observation_id for item in snapshot.iot_evidence] == ["iot-0"]


@pytest.mark.parametrize(
    ("context", "cutoff", "reason"),
    [
        (_context(), CUTOFF.replace(tzinfo=None), "invalid_cutoff"),
        (_context(events=(_event(-1, 1.3), _event(0, 1.2), _event(20, 1.1))), CUTOFF, "future_observation"),
        (_context(events=(_event(20, 1.1), _event(0, 120, "umol/L"))), CUTOFF, "invalid_ehr_unit"),
        (_context(observations=(_observation(0, unit="kPa"),)), CUTOFF, "invalid_iot_unit"),
        (_context(events=(_event(20, 1.1), _event(0, "1.2"))), CUTOFF, "invalid_ehr_value"),
        (_context(observations=(_observation(25),)), CUTOFF, "stale_iot_observation"),
        (_context(events=(replace(_event(20, 1.1), source="unknown"), _event(0, 1.2))), CUTOFF, "invalid_ehr_provenance"),
        (_context(events=(replace(_event(20, 1.1), patient_id="tbp-other"), _event(0, 1.2))), CUTOFF, "invalid_ehr_ownership"),
    ],
)
def test_snapshot_rejects_invalid_or_unsafe_inputs(context: ClinicalContext, cutoff: datetime, reason: str) -> None:
    snapshot = build_prediction_snapshot(context, cutoff)

    assert snapshot.status == "unavailable"
    assert snapshot.reason == reason
    assert snapshot.frame is None


def test_forbidden_or_unknown_feature_payload_fields_are_rejected() -> None:
    context = _context(events=(_event(20, 1.1), _event(0, 1.2, scenario="leakage")))

    snapshot = build_prediction_snapshot(context, CUTOFF)

    assert snapshot.status == "unavailable"
    assert snapshot.reason == "forbidden_ehr_field"


def test_training_labels_only_new_supported_aki_in_the_open_24_hour_window() -> None:
    events = (
        _event(20, 1.1), _event(0, 1.2),
        replace(_event(0, 1.2), event_id="ehr-at-cutoff"),
        replace(_event(-2, 1.51), event_id="ehr-in-window"),
        replace(_event(-25, 2.0), event_id="ehr-after-window"),
    )

    rows = build_training_rows([_context(events=events)], [CUTOFF])

    assert tuple(rows.features.columns) == FEATURE_SCHEMA.columns
    assert rows.labels == (1,)
    assert rows.patient_groups == (PATIENT_ID,)
    assert rows.cutoffs == (CUTOFF,)
