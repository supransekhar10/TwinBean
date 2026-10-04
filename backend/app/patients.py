"""Firestore repository helpers for TwinBean's synthetic patient cohorts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from pydantic import BaseModel

from .firestore import get_firestore_client
from .synthetic_data import EhrEvent, IotObservation, SyntheticCohort, SyntheticPatient


MAX_SEED_PATIENTS = 100
MAX_RECORDS_PER_PATIENT = 100
MAX_HISTORY_RECORDS = 500
MAX_WRITES_PER_BATCH = 100
MAX_BATCH_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_BYTES = 900 * 1024
COHORTS_COLLECTION = "twinbean_cohorts"
ACTIVE_COHORT_PATH = "twinbean_metadata/active_cohort"
_PATIENT_ID = re.compile(r"^tbp-[0-9a-f]{32}$")
_EHR_EVENT_ID = re.compile(r"^ehr-[0-9a-f]{32}$")
_IOT_OBSERVATION_ID = re.compile(r"^iot-[0-9a-f]{32}$")
_COHORT_ID = re.compile(r"^cohort-[0-9a-f]{24}$")
_EHR_SOURCE = "twinbean-synthetic-ehr"
_IOT_SOURCE = "twinbean-simulated-iot"
_COHORT_SOURCE = "twinbean-synthetic-generator"


class PatientSummary(BaseModel):
    """Root patient data safe to return from the bounded list endpoint."""

    patient_id: str
    display_name: str
    age: int
    ckd_stage: str


class PatientDetail(BaseModel):
    """One patient with explicitly separate EHR and simulated IoT histories."""

    patient: PatientSummary
    ehr_history: list[EhrEvent]
    iot_observations: list[IotObservation]


@dataclass(frozen=True)
class SeedResult:
    """Non-sensitive deterministic result of a synthetic cohort seed."""

    cohort_id: str
    patient_count: int
    ehr_event_count: int
    iot_observation_count: int
    write_count: int
    manifest_checksum: str


@dataclass(frozen=True)
class _ActiveCohort:
    cohort_id: str
    manifest_checksum: str
    patient_count: int
    ehr_event_count: int
    iot_observation_count: int
    generator_version: str
    seed: int
    source: str


@dataclass(frozen=True)
class ClinicalContext:
    """Immutable active-cohort data available to one clinical-result operation."""

    cohort_id: str
    manifest_checksum: str
    generator_version: str
    seed: int
    patient: PatientDetail


class PatientRepository:
    """Server-only Firestore reads and validated immutable cohort publication."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_firestore(cls) -> "PatientRepository":
        return cls(get_firestore_client())

    def list_patients(self, limit: int) -> list[PatientSummary]:
        active = self._load_active_cohort()
        if active is None:
            return []
        bounded_limit = min(max(limit, 1), 100)
        snapshots = (
            self._cohort_document(active.cohort_id)
            .collection("patients")
            .order_by("patient_id")
            .limit(bounded_limit)
            .stream()
        )
        return [self._summary_from_data(snapshot.to_dict() or {}, active) for snapshot in snapshots]

    def get_patient(self, patient_id: str, event_limit: int = 100) -> PatientDetail | None:
        """Read one active owned root and its independent EHR and IoT streams."""
        if not _PATIENT_ID.fullmatch(patient_id):
            raise ValueError("patient identifier must be a stable TwinBean identifier")
        active = self._load_active_cohort()
        if active is None:
            return None
        return self._get_patient_for_active(active, patient_id, event_limit)

    def get_clinical_context(self, patient_id: str) -> ClinicalContext | None:
        """Resolve one patient from the validated active immutable cohort only."""
        if not _PATIENT_ID.fullmatch(patient_id):
            raise ValueError("patient identifier must be a stable TwinBean identifier")
        active = self._load_active_cohort()
        if active is None:
            return None
        patient = self._get_patient_for_active(active, patient_id, MAX_HISTORY_RECORDS)
        if patient is None:
            return None
        return ClinicalContext(
            cohort_id=active.cohort_id,
            manifest_checksum=active.manifest_checksum,
            generator_version=active.generator_version,
            seed=active.seed,
            patient=patient,
        )

    def write_clinical_results(self, context: ClinicalContext, envelope: Any) -> str:
        """Persist one validated rule and one prediction in a single immutable batch."""
        active = self._load_active_cohort()
        if active is None or (active.cohort_id, active.manifest_checksum) != (
            context.cohort_id,
            context.manifest_checksum,
        ):
            raise ValueError("clinical context no longer belongs to the active immutable cohort")
        patient_id = context.patient.patient_id
        rule_payload = envelope.clinical_rule.model_dump(mode="json")
        prediction_payload = envelope.prediction.model_dump(mode="json")
        result_id = _clinical_result_id(context, rule_payload, prediction_payload)
        rule_document = _clinical_result_payload(
            context, patient_id, result_id, "clinical_rule", rule_payload
        )
        prediction_document = _clinical_result_payload(
            context, patient_id, result_id, "aki_prediction", prediction_payload
        )
        _validate_clinical_result_payload(rule_document, "clinical_rule")
        _validate_clinical_result_payload(prediction_document, "aki_prediction")
        patient_path = _patient_path(context.cohort_id, patient_id)
        batch = self._client.batch()
        batch.set(self._client.document(f"{patient_path}/clinical_rules/{result_id}"), rule_document)
        batch.set(self._client.document(f"{patient_path}/aki_predictions/{result_id}"), prediction_document)
        batch.commit()
        return result_id

    def _get_patient_for_active(
        self, active: _ActiveCohort, patient_id: str, event_limit: int
    ) -> PatientDetail | None:
        document = self._cohort_document(active.cohort_id).collection("patients").document(patient_id)
        root_data = document.get().to_dict()
        if root_data is None:
            return None
        patient = self._summary_from_data(root_data, active)
        bounded_limit = min(max(event_limit, 1), MAX_HISTORY_RECORDS)
        ehr_events = document.collection("ehr_events").order_by("event_time").limit(bounded_limit).stream()
        iot_observations = document.collection("iot_observations").order_by("observed_at").limit(bounded_limit).stream()
        ehr_history = sorted(
            (self._ehr_event_from_data(snapshot.to_dict() or {}, active, patient_id) for snapshot in ehr_events),
            key=lambda event: event.event_time,
        )
        iot_history = sorted(
            (self._iot_observation_from_data(snapshot.to_dict() or {}, active, patient_id) for snapshot in iot_observations),
            key=lambda observation: observation.observed_at,
        )
        return PatientDetail(patient=patient, ehr_history=ehr_history, iot_observations=iot_history)

    def write_cohort(self, cohort: SyntheticCohort) -> SeedResult:
        """Stage, read back, validate, then atomically publish one cohort pointer.

        Existing versions and unrelated Firestore data are deliberately never deleted.
        A failed stage, validation, or activation therefore leaves the prior pointer intact.
        """
        relative_manifest = self._build_manifest(cohort)
        cohort_id = _cohort_id(relative_manifest)
        manifest = _versioned_manifest(cohort_id, relative_manifest)
        checksum = _manifest_checksum(manifest)
        descriptor = _cohort_descriptor(cohort, cohort_id, checksum)
        for chunk in _batch_chunks([*manifest, (_cohort_path(cohort_id), descriptor)]):
            batch = self._client.batch()
            for path, payload in chunk:
                batch.set(self._client.document(path), payload)
            batch.commit()

        active = self._validate_staged_cohort(cohort_id)
        if active.manifest_checksum != checksum:
            raise ValueError("staged cohort checksum does not match the generated manifest")
        self._activate(active)
        return SeedResult(
            cohort_id=cohort_id,
            patient_count=active.patient_count,
            ehr_event_count=active.ehr_event_count,
            iot_observation_count=active.iot_observation_count,
            write_count=len(manifest) + 2,  # staged records + descriptor + active pointer
            manifest_checksum=checksum,
        )

    def _activate(self, active: _ActiveCohort) -> None:
        transaction = self._client.transaction()
        transaction.set(
            self._client.document(ACTIVE_COHORT_PATH),
            {
                "cohort_id": active.cohort_id,
                "manifest_checksum": active.manifest_checksum,
                "patient_count": active.patient_count,
                "ehr_event_count": active.ehr_event_count,
                "iot_observation_count": active.iot_observation_count,
                "generator_version": active.generator_version,
                "seed": active.seed,
                "synthetic": True,
                "source": _COHORT_SOURCE,
            },
        )
        transaction.commit()

    def _load_active_cohort(self) -> _ActiveCohort | None:
        pointer = self._client.document(ACTIVE_COHORT_PATH).get().to_dict()
        if pointer is None:
            return None
        active = _active_from_data(pointer)
        staged = self._validate_staged_cohort(active.cohort_id)
        if staged != active:
            raise ValueError("active cohort pointer does not exactly match its validated cohort")
        return active

    def _validate_staged_cohort(self, cohort_id: str) -> _ActiveCohort:
        if not _COHORT_ID.fullmatch(cohort_id):
            raise ValueError("cohort identifier is not a TwinBean immutable version")
        descriptor = self._cohort_document(cohort_id).get().to_dict()
        active = _active_from_data(descriptor or {})
        if active.cohort_id != cohort_id:
            raise ValueError("staged cohort descriptor ownership does not match its path")
        manifest: list[tuple[str, dict[str, object]]] = []
        patient_snapshots = self._cohort_document(cohort_id).collection("patients").stream()
        patient_count = ehr_count = iot_count = 0
        for root_snapshot in patient_snapshots:
            root_data = root_snapshot.to_dict() or {}
            patient = self._summary_from_data(root_data, active)
            _require_snapshot_id(root_snapshot, patient.patient_id)
            patient_count += 1
            root_path = _patient_path(cohort_id, patient.patient_id)
            manifest.append((root_path, dict(root_data)))
            document = self._client.document(root_path)
            for snapshot in document.collection("ehr_events").stream():
                data = snapshot.to_dict() or {}
                event = self._ehr_event_from_data(data, active, patient.patient_id)
                _require_snapshot_id(snapshot, event.event_id)
                ehr_count += 1
                manifest.append((f"{root_path}/ehr_events/{event.event_id}", dict(data)))
            for snapshot in document.collection("iot_observations").stream():
                data = snapshot.to_dict() or {}
                observation = self._iot_observation_from_data(data, active, patient.patient_id)
                _require_snapshot_id(snapshot, observation.observation_id)
                iot_count += 1
                manifest.append((f"{root_path}/iot_observations/{observation.observation_id}", dict(data)))
        if (patient_count, ehr_count, iot_count) != (
            active.patient_count,
            active.ehr_event_count,
            active.iot_observation_count,
        ):
            raise ValueError("staged cohort document counts do not match its descriptor")
        if _manifest_checksum(manifest) != active.manifest_checksum:
            raise ValueError("staged cohort manifest checksum does not match its descriptor")
        return active

    def _cohort_document(self, cohort_id: str) -> Any:
        return self._client.document(_cohort_path(cohort_id))

    @staticmethod
    def _summary_from_data(data: Mapping[str, object], active: _ActiveCohort) -> PatientSummary:
        _validate_stored_provenance(data, active, _EHR_SOURCE)
        patient_id = _required_identifier(data, "patient_id", _PATIENT_ID)
        display_name = _required_str(data, "display_name")
        age = data.get("age")
        stage = _required_str(data, "ckd_stage")
        if not isinstance(age, int) or isinstance(age, bool) or age < 18:
            raise ValueError("stored patient age must be an adult integer")
        _utc_timestamp(data.get("created_at"))
        return PatientSummary(patient_id=patient_id, display_name=display_name, age=age, ckd_stage=stage)

    @staticmethod
    def _ehr_event_from_data(data: Mapping[str, object], active: _ActiveCohort, patient_id: str) -> EhrEvent:
        _validate_stored_provenance(data, active, _EHR_SOURCE, patient_id)
        return EhrEvent(
            event_id=_required_identifier(data, "event_id", _EHR_EVENT_ID),
            patient_id=patient_id,
            event_type=_required_str(data, "event_type"),
            event_time=_utc_timestamp(data.get("event_time")),
            data=_record_data(data),
            synthetic=True,
            generator_version=active.generator_version,
            seed=active.seed,
            source=_EHR_SOURCE,
        )

    @staticmethod
    def _iot_observation_from_data(data: Mapping[str, object], active: _ActiveCohort, patient_id: str) -> IotObservation:
        _validate_stored_provenance(data, active, _IOT_SOURCE, patient_id)
        return IotObservation(
            observation_id=_required_identifier(data, "observation_id", _IOT_OBSERVATION_ID),
            patient_id=patient_id,
            measurement_type=_required_str(data, "measurement_type"),
            observed_at=_utc_timestamp(data.get("observed_at")),
            data=_record_data(data),
            synthetic=True,
            generator_version=active.generator_version,
            seed=active.seed,
            source=_IOT_SOURCE,
        )

    @staticmethod
    def _build_manifest(cohort: SyntheticCohort) -> list[tuple[str, dict[str, object]]]:
        _validate_cohort_provenance(cohort)
        patients = tuple(cohort.patients)
        if not 1 <= len(patients) <= MAX_SEED_PATIENTS:
            raise ValueError(f"cohort patient count must be between 1 and {MAX_SEED_PATIENTS}")
        patient_ids: set[str] = set()
        manifest: list[tuple[str, dict[str, object]]] = []
        for patient in patients:
            _validate_patient(patient, cohort)
            if patient.patient_id in patient_ids:
                raise ValueError("cohort patient identifiers must be unique")
            patient_ids.add(patient.patient_id)
            manifest.append((f"patients/{patient.patient_id}", patient.to_dict()))
        _validate_record_counts(cohort, patient_ids)
        for event in cohort.ehr_events:
            _validate_ehr_event(event, cohort, patient_ids)
            manifest.append((f"patients/{event.patient_id}/ehr_events/{event.event_id}", event.to_dict()))
        for observation in cohort.iot_observations:
            _validate_iot_observation(observation, cohort, patient_ids)
            manifest.append((f"patients/{observation.patient_id}/iot_observations/{observation.observation_id}", observation.to_dict()))
        _validate_manifest(manifest)
        return manifest


def _cohort_path(cohort_id: str) -> str:
    return f"{COHORTS_COLLECTION}/{cohort_id}"


def _patient_path(cohort_id: str, patient_id: str) -> str:
    return f"{_cohort_path(cohort_id)}/patients/{patient_id}"


def _clinical_result_id(
    context: ClinicalContext,
    rule_payload: Mapping[str, object],
    prediction_payload: Mapping[str, object],
) -> str:
    identity = {
        "cohort_id": context.cohort_id,
        "patient_id": context.patient.patient_id,
        "prediction_cutoff": prediction_payload["prediction_cutoff"],
        "rule_version": rule_payload["rule_version"],
        "outcome": prediction_payload["outcome"],
        "model_version": prediction_payload.get("model_version") or "unavailable-engine-v1",
        "feature_schema_version": prediction_payload.get("feature_schema_version") or "unavailable-schema-v1",
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"clinical-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]}"


def _clinical_result_payload(
    context: ClinicalContext,
    patient_id: str,
    result_id: str,
    result_type: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        **dict(payload),
        "result_id": result_id,
        "result_type": result_type,
        "patient_id": patient_id,
        "cohort_id": context.cohort_id,
        "manifest_checksum": context.manifest_checksum,
        "generator_version": context.generator_version,
        "seed": context.seed,
        "synthetic": True,
        "data_classification": "synthetic",
        "source": "twinbean-clinical-result",
    }


def _validate_clinical_result_payload(payload: Mapping[str, object], result_type: str) -> None:
    if payload.get("result_type") != result_type:
        raise ValueError("clinical result type must match its owned collection")
    if not isinstance(payload.get("result_id"), str) or not str(payload["result_id"]).startswith("clinical-"):
        raise ValueError("clinical result must have a deterministic owned identifier")
    if payload.get("synthetic") is not True or payload.get("data_classification") != "synthetic":
        raise ValueError("clinical results must retain synthetic provenance")
    if payload.get("source") != "twinbean-clinical-result":
        raise ValueError("clinical result source must be TwinBean-owned")
    if result_type == "clinical_rule":
        forbidden = {"probability", "attributions", "reasons", "outcome"}
    else:
        forbidden = {"evidence", "scope", "limitation", "rule_version"}
        if payload.get("status") == "unavailable" and ({"probability", "attributions"} & set(payload)):
            raise ValueError("unavailable prediction must not include probability or attributions")
    if forbidden & set(payload):
        raise ValueError("clinical rule and prediction fields must remain separate")
    if _encoded_size(dict(payload)) >= MAX_DOCUMENT_BYTES:
        raise ValueError("clinical result payload must be smaller than 900 KiB")


def _cohort_id(manifest: list[tuple[str, dict[str, object]]]) -> str:
    return f"cohort-{_manifest_checksum(manifest)[:24]}"


def _versioned_manifest(cohort_id: str, manifest: list[tuple[str, dict[str, object]]]) -> list[tuple[str, dict[str, object]]]:
    return [
        (f"{_cohort_path(cohort_id)}/{path}", {**payload, "cohort_id": cohort_id})
        for path, payload in manifest
    ]


def _cohort_descriptor(cohort: SyntheticCohort, cohort_id: str, checksum: str) -> dict[str, object]:
    provenance = cohort.provenance
    return {
        "cohort_id": cohort_id,
        "manifest_checksum": checksum,
        "patient_count": len(cohort.patients),
        "ehr_event_count": len(cohort.ehr_events),
        "iot_observation_count": len(cohort.iot_observations),
        "generator_version": provenance.generator_version,
        "seed": provenance.seed,
        "synthetic": True,
        "source": _COHORT_SOURCE,
        "time_basis": provenance.to_dict()["time_basis"],
        "generated_at": provenance.to_dict()["generated_at"],
    }


def _active_from_data(data: Mapping[str, object]) -> _ActiveCohort:
    if data.get("synthetic") is not True or data.get("source") != _COHORT_SOURCE:
        raise ValueError("cohort metadata must be exact TwinBean synthetic provenance")
    cohort_id = _required_identifier(data, "cohort_id", _COHORT_ID)
    checksum = _required_str(data, "manifest_checksum")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("cohort manifest checksum must be a SHA-256 digest")
    counts = tuple(data.get(key) for key in ("patient_count", "ehr_event_count", "iot_observation_count"))
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        raise ValueError("cohort metadata counts must be non-negative integers")
    seed = data.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("cohort metadata seed must be an integer")
    generator_version = _required_str(data, "generator_version")
    if "time_basis" in data:
        _utc_timestamp(data["time_basis"])
    if "generated_at" in data:
        _utc_timestamp(data["generated_at"])
    return _ActiveCohort(cohort_id, checksum, counts[0], counts[1], counts[2], generator_version, seed, _COHORT_SOURCE)


def _validate_stored_provenance(data: Mapping[str, object], active: _ActiveCohort, source: str, patient_id: str | None = None) -> None:
    if data.get("synthetic") is not True or data.get("source") != source:
        raise ValueError("stored record must have exact TwinBean synthetic provenance")
    if data.get("cohort_id") != active.cohort_id:
        raise ValueError("stored record cohort ownership does not match the active cohort")
    if data.get("generator_version") != active.generator_version or data.get("seed") != active.seed:
        raise ValueError("stored record provenance does not match the active cohort")
    if patient_id is not None and data.get("patient_id") != patient_id:
        raise ValueError("stored child record does not belong to its parent patient")


def _required_str(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"stored {key} must be a non-empty string")
    return value


def _required_identifier(data: Mapping[str, object], key: str, pattern: re.Pattern[str]) -> str:
    value = _required_str(data, key)
    if not pattern.fullmatch(value):
        raise ValueError(f"stored {key} is not a TwinBean-owned identifier")
    return value


def _require_snapshot_id(snapshot: Any, expected: str) -> None:
    if getattr(snapshot, "id", None) != expected:
        raise ValueError("stored document path ownership does not match its payload identifier")


def _utc_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("Firestore record timestamps must be UTC datetimes or ISO timestamps")
    if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(None):
        raise ValueError("Firestore record timestamps must be timezone-aware UTC")
    return timestamp.astimezone(UTC)


def _record_data(record: Mapping[str, object]) -> Mapping[str, object]:
    value = record.get("data")
    if not isinstance(value, Mapping):
        raise ValueError("Firestore record data must be a mapping")
    return dict(value)


def _validate_cohort_provenance(cohort: SyntheticCohort) -> None:
    provenance = cohort.provenance
    if provenance.synthetic is not True or provenance.source != _COHORT_SOURCE:
        raise ValueError("cohort provenance must be exact synthetic TwinBean generator data")
    if not provenance.generator_version.strip():
        raise ValueError("cohort provenance must include a generator version")
    _utc_timestamp(provenance.to_dict()["time_basis"])
    _utc_timestamp(provenance.to_dict()["generated_at"])


def _validate_patient(patient: SyntheticPatient, cohort: SyntheticCohort) -> None:
    if not _PATIENT_ID.fullmatch(patient.patient_id):
        raise ValueError("patient path must use a TwinBean-owned patient identifier")
    _validate_record_provenance(patient, cohort, _EHR_SOURCE)
    _utc_timestamp(patient.to_dict()["created_at"])


def _validate_ehr_event(event: EhrEvent, cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    if not _EHR_EVENT_ID.fullmatch(event.event_id) or event.patient_id not in patient_ids:
        raise ValueError("EHR event path must have a generated TwinBean parent and identifier")
    _validate_record_provenance(event, cohort, _EHR_SOURCE)
    _utc_timestamp(event.to_dict()["event_time"])


def _validate_iot_observation(observation: IotObservation, cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    if not _IOT_OBSERVATION_ID.fullmatch(observation.observation_id) or observation.patient_id not in patient_ids:
        raise ValueError("IoT observation path must have a generated TwinBean parent and identifier")
    _validate_record_provenance(observation, cohort, _IOT_SOURCE)
    _utc_timestamp(observation.to_dict()["observed_at"])


def _validate_record_provenance(record: SyntheticPatient | EhrEvent | IotObservation, cohort: SyntheticCohort, source: str) -> None:
    provenance = cohort.provenance
    if record.synthetic is not True or record.source != source:
        raise ValueError("every persisted record must have exact synthetic TwinBean provenance")
    if record.generator_version != provenance.generator_version or record.seed != provenance.seed:
        raise ValueError("record provenance must match the cohort generator version and seed")


def _validate_record_counts(cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    counts: Counter[str] = Counter(record.patient_id for record in (*cohort.ehr_events, *cohort.iot_observations))
    if any(record.patient_id not in patient_ids for record in (*cohort.ehr_events, *cohort.iot_observations)):
        raise ValueError("record parent must be a generated TwinBean patient")
    if any(count > MAX_RECORDS_PER_PATIENT for count in counts.values()):
        raise ValueError(f"cohort records per patient must not exceed {MAX_RECORDS_PER_PATIENT}")


def _validate_manifest(manifest: list[tuple[str, dict[str, object]]]) -> None:
    paths: set[str] = set()
    for path, payload in manifest:
        if path in paths:
            raise ValueError("cohort manifest paths must be unique")
        paths.add(path)
        if payload.get("synthetic") is not True or _encoded_size(payload) >= MAX_DOCUMENT_BYTES:
            raise ValueError("persisted payload must be explicit synthetic data smaller than 900 KiB")


def _batch_chunks(manifest: list[tuple[str, dict[str, object]]]) -> list[list[tuple[str, dict[str, object]]]]:
    chunks: list[list[tuple[str, dict[str, object]]]] = []
    current: list[tuple[str, dict[str, object]]] = []
    current_bytes = 0
    for path, payload in manifest:
        entry_bytes = len(path.encode("utf-8")) + _encoded_size(payload)
        if current and (len(current) >= MAX_WRITES_PER_BATCH or current_bytes + entry_bytes >= MAX_BATCH_BYTES):
            chunks.append(current)
            current, current_bytes = [], 0
        current.append((path, payload))
        current_bytes += entry_bytes
    if current:
        chunks.append(current)
    return chunks


def _encoded_size(payload: dict[str, object]) -> int:
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def _manifest_checksum(manifest: list[tuple[str, dict[str, object]]]) -> str:
    encoded = json.dumps(sorted(manifest, key=lambda entry: entry[0]), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
