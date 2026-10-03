"""Firestore repository helpers for TwinBean's synthetic patient cohort."""

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
_PATIENT_ID = re.compile(r"^tbp-[0-9a-f]{32}$")
_EHR_EVENT_ID = re.compile(r"^ehr-[0-9a-f]{32}$")
_IOT_OBSERVATION_ID = re.compile(r"^iot-[0-9a-f]{32}$")


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

    patient_count: int
    ehr_event_count: int
    iot_observation_count: int
    write_count: int
    manifest_checksum: str


class PatientRepository:
    """Server-only Firestore reads and bounded synthetic cohort writes."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_firestore(cls) -> "PatientRepository":
        return cls(get_firestore_client())

    def list_patients(self, limit: int) -> list[PatientSummary]:
        bounded_limit = min(max(limit, 1), 100)
        snapshots = (
            self._client.collection("patients")
            .order_by("patient_id")
            .limit(bounded_limit)
            .stream()
        )
        return [self._summary_from_snapshot(snapshot) for snapshot in snapshots]

    def get_patient(self, patient_id: str, event_limit: int = 100) -> PatientDetail | None:
        """Read one owned root and its bounded EHR and IoT streams independently."""
        if not _PATIENT_ID.fullmatch(patient_id):
            raise ValueError("patient identifier must be a stable TwinBean identifier")

        document = self._client.document(f"patients/{patient_id}")
        root_snapshot = document.get()
        root_data = root_snapshot.to_dict()
        if root_data is None:
            return None

        bounded_limit = min(max(event_limit, 1), MAX_HISTORY_RECORDS)
        ehr_events = (
            document.collection("ehr_events")
            .order_by("event_time")
            .limit(bounded_limit)
            .stream()
        )
        iot_observations = (
            document.collection("iot_observations")
            .order_by("observed_at")
            .limit(bounded_limit)
            .stream()
        )
        return PatientDetail(
            patient=self._summary_from_data(root_data),
            ehr_history=[self._ehr_event_from_snapshot(snapshot) for snapshot in ehr_events],
            iot_observations=[
                self._iot_observation_from_snapshot(snapshot) for snapshot in iot_observations
            ],
        )

    def write_cohort(self, cohort: SyntheticCohort) -> SeedResult:
        """Write a prevalidated owned-path manifest using only ``set`` batches."""
        manifest = self._build_manifest(cohort)
        checksum = _manifest_checksum(manifest)
        for chunk in _batch_chunks(manifest):
            batch = self._client.batch()
            for path, payload in chunk:
                batch.set(self._client.document(path), payload)
            batch.commit()
        return SeedResult(
            patient_count=len(cohort.patients),
            ehr_event_count=len(cohort.ehr_events),
            iot_observation_count=len(cohort.iot_observations),
            write_count=len(manifest),
            manifest_checksum=checksum,
        )

    @staticmethod
    def _summary_from_snapshot(snapshot: Any) -> PatientSummary:
        return PatientRepository._summary_from_data(snapshot.to_dict() or {})

    @staticmethod
    def _summary_from_data(data: Mapping[str, object]) -> PatientSummary:
        return PatientSummary(
            patient_id=str(data["patient_id"]),
            display_name=str(data["display_name"]),
            age=int(data["age"]),
            ckd_stage=str(data["ckd_stage"]),
        )

    @staticmethod
    def _ehr_event_from_snapshot(snapshot: Any) -> EhrEvent:
        data = snapshot.to_dict() or {}
        return EhrEvent(
            event_id=str(data["event_id"]),
            patient_id=str(data["patient_id"]),
            event_type=str(data["event_type"]),
            event_time=_utc_timestamp(data["event_time"]),
            data=_record_data(data),
            synthetic=bool(data["synthetic"]),
            generator_version=str(data["generator_version"]),
            seed=int(data["seed"]),
            source=str(data["source"]),
        )

    @staticmethod
    def _iot_observation_from_snapshot(snapshot: Any) -> IotObservation:
        data = snapshot.to_dict() or {}
        return IotObservation(
            observation_id=str(data["observation_id"]),
            patient_id=str(data["patient_id"]),
            measurement_type=str(data["measurement_type"]),
            observed_at=_utc_timestamp(data["observed_at"]),
            data=_record_data(data),
            synthetic=bool(data["synthetic"]),
            generator_version=str(data["generator_version"]),
            seed=int(data["seed"]),
            source=str(data["source"]),
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
    value = record.get("data", {})
    if not isinstance(value, Mapping):
        raise ValueError("Firestore record data must be a mapping")
    return dict(value)


def _validate_cohort_provenance(cohort: SyntheticCohort) -> None:
    provenance = cohort.provenance
    if not provenance.synthetic or not provenance.source.startswith("twinbean-"):
        raise ValueError("cohort provenance must be explicitly synthetic TwinBean data")
    if not provenance.generator_version.strip():
        raise ValueError("cohort provenance must include a generator version")


def _validate_patient(patient: SyntheticPatient, cohort: SyntheticCohort) -> None:
    if not _PATIENT_ID.fullmatch(patient.patient_id):
        raise ValueError("patient path must use a TwinBean-owned patient identifier")
    _validate_record_provenance(patient, cohort)


def _validate_ehr_event(event: EhrEvent, cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    if not _EHR_EVENT_ID.fullmatch(event.event_id):
        raise ValueError("EHR event path must use a TwinBean-owned event identifier")
    if event.patient_id not in patient_ids:
        raise ValueError("EHR event parent must be a generated TwinBean patient")
    _validate_record_provenance(event, cohort)


def _validate_iot_observation(observation: IotObservation, cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    if not _IOT_OBSERVATION_ID.fullmatch(observation.observation_id):
        raise ValueError("IoT observation path must use a TwinBean-owned observation identifier")
    if observation.patient_id not in patient_ids:
        raise ValueError("IoT observation parent must be a generated TwinBean patient")
    _validate_record_provenance(observation, cohort)


def _validate_record_provenance(record: SyntheticPatient | EhrEvent | IotObservation, cohort: SyntheticCohort) -> None:
    provenance = cohort.provenance
    if not record.synthetic or not record.source.startswith("twinbean-"):
        raise ValueError("every persisted record must be explicitly synthetic TwinBean data")
    if record.generator_version != provenance.generator_version or record.seed != provenance.seed:
        raise ValueError("record provenance must match the cohort generator version and seed")


def _validate_record_counts(cohort: SyntheticCohort, patient_ids: set[str]) -> None:
    counts: Counter[str] = Counter()
    for record in (*cohort.ehr_events, *cohort.iot_observations):
        if record.patient_id not in patient_ids:
            raise ValueError("record parent must be a generated TwinBean patient")
        counts[record.patient_id] += 1
    if any(count > MAX_RECORDS_PER_PATIENT for count in counts.values()):
        raise ValueError(f"cohort records per patient must not exceed {MAX_RECORDS_PER_PATIENT}")


def _validate_manifest(manifest: list[tuple[str, dict[str, object]]]) -> None:
    paths: set[str] = set()
    for path, payload in manifest:
        if path in paths:
            raise ValueError("cohort manifest paths must be unique")
        paths.add(path)
        if payload.get("synthetic") is not True:
            raise ValueError("every persisted payload must be explicitly synthetic")
        if _encoded_size(payload) >= MAX_DOCUMENT_BYTES:
            raise ValueError("document payload must be smaller than 900 KiB")


def _batch_chunks(manifest: list[tuple[str, dict[str, object]]]) -> list[list[tuple[str, dict[str, object]]]]:
    chunks: list[list[tuple[str, dict[str, object]]]] = []
    current: list[tuple[str, dict[str, object]]] = []
    current_bytes = 0
    for path, payload in manifest:
        entry = (path, payload)
        entry_bytes = len(path.encode("utf-8")) + _encoded_size(payload)
        if current and (len(current) >= MAX_WRITES_PER_BATCH or current_bytes + entry_bytes >= MAX_BATCH_BYTES):
            chunks.append(current)
            current, current_bytes = [], 0
        current.append(entry)
        current_bytes += entry_bytes
    if current:
        chunks.append(current)
    return chunks


def _encoded_size(payload: dict[str, object]) -> int:
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def _manifest_checksum(manifest: list[tuple[str, dict[str, object]]]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
