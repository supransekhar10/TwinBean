"""Firestore repository helpers for TwinBean's synthetic patient cohorts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Annotated, Any, Literal, Mapping

from google.api_core.retry import Retry
from pydantic import BaseModel, ConfigDict, Field

from .firestore import get_firestore_client
from .synthetic_data import EhrEvent, IotObservation, SyntheticCohort, SyntheticPatient


MAX_SEED_PATIENTS = 100
MAX_RECORDS_PER_PATIENT = 100
MAX_HISTORY_RECORDS = 500
MAX_CLINICAL_RESULT_RECORDS = 100
MAX_WRITES_PER_BATCH = 100
MAX_BATCH_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_BYTES = 900 * 1024
DASHBOARD_CACHE_TTL_SECONDS = 300.0
FIRESTORE_READ_TIMEOUT_SECONDS = 3.0
# Interactive reads fail fast. The UI owns retry so SDK-level retries cannot
# leave clinicians staring at an indefinite loading state.
_FIRESTORE_READ_RETRY = Retry(
    predicate=lambda _error: False,
    deadline=FIRESTORE_READ_TIMEOUT_SECONDS,
)
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
    sex: str | None = None
    ckd_stage: str
    ckd_context: str | None = None


class PatientDetail(BaseModel):
    """One patient with explicitly separate EHR and simulated IoT histories."""

    patient: PatientSummary
    ehr_history: list[EhrEvent]
    iot_observations: list[IotObservation]


class DashboardClinicalRuleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["criteria_met", "criteria_not_met", "insufficient_creatinine_history"]
    calculation_time: datetime
    prediction_cutoff: datetime
    insufficiency_reasons: list[str] = Field(default_factory=list)


class AvailableDashboardPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["available"]
    probability: float = Field(ge=0.0, le=1.0)
    prediction_cutoff: datetime
    generated_at: datetime
    warnings: list[str] = Field(default_factory=list)


class UnavailableDashboardPrediction(BaseModel):
    """Unavailable has no probability field, so missing risk cannot serialize as zero."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["unavailable"]
    prediction_cutoff: datetime | None = None
    generated_at: datetime | None = None
    reasons: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)


DashboardPredictionSummary = Annotated[
    AvailableDashboardPrediction | UnavailableDashboardPrediction,
    Field(discriminator="status"),
]


class DashboardPatient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient: PatientSummary
    current_rule: DashboardClinicalRuleSummary | None
    prediction: DashboardPredictionSummary
    latest_review_at: datetime | None = None


class ReviewNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_id: str
    patient_id: str
    author_uid: str
    text: str
    created_at: datetime


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
        self._disk_cache_enabled = client.__class__.__module__.startswith("google.cloud.firestore")
        self._dashboard_cache: dict[int, tuple[float, tuple[DashboardPatient, ...]]] = {}

    @classmethod
    def from_firestore(cls) -> "PatientRepository":
        return cls(get_firestore_client())

    def list_patients(self, limit: int) -> list[PatientSummary]:
        active = self._load_active_cohort()
        if active is None:
            return []
        return self._list_patients_for_active(active, limit)

    def _list_patients_for_active(self, active: _ActiveCohort, limit: int) -> list[PatientSummary]:
        bounded_limit = min(max(limit, 1), 100)
        snapshots = (
            self._cohort_document(active.cohort_id)
            .collection("patients")
            .order_by("patient_id")
            .limit(bounded_limit)
            .stream(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
        )
        return [self._summary_from_data(snapshot.to_dict() or {}, active) for snapshot in snapshots]

    def list_dashboard_patients(self, limit: int, refresh: bool = False) -> list[DashboardPatient]:
        """Project only latest stored evidence; this method never invokes prediction."""
        from .clinical_rules import ClinicalRuleResult
        from .prediction_service import validate_aki_prediction_result

        bounded_limit = min(max(limit, 1), MAX_SEED_PATIENTS)
        cached = None if refresh else self._dashboard_cache.get(bounded_limit)
        now = monotonic()
        if cached is not None and cached[0] > now:
            return [row.model_copy(deep=True) for row in cached[1]]
        if not refresh and self._disk_cache_enabled:
            disk_rows = self._load_dashboard_disk_cache(bounded_limit)
            if disk_rows is not None:
                self._dashboard_cache[bounded_limit] = (
                    now + DASHBOARD_CACHE_TTL_SECONDS,
                    tuple(row.model_copy(deep=True) for row in disk_rows),
                )
                return disk_rows

        active = self._load_active_cohort()
        if active is None:
            return []
        rows: list[DashboardPatient] = []
        review_statuses = self._load_review_statuses()
        for patient in self._list_patients_for_active(active, bounded_limit):
            rules = [
                ClinicalRuleResult.model_validate(payload)
                for payload in self._list_clinical_result_payloads_for_active(
                    active, patient.patient_id, 1, "clinical_rules", "clinical_rule", "calculation_time"
                )
            ]
            predictions = [
                validate_aki_prediction_result(payload)
                for payload in self._list_clinical_result_payloads_for_active(
                    active, patient.patient_id, 1, "aki_predictions", "aki_prediction", "generated_at"
                )
            ]
            current_rule = None
            if rules:
                rule = rules[0]
                current_rule = DashboardClinicalRuleSummary(
                    status=rule.status,
                    calculation_time=rule.calculation_time,
                    prediction_cutoff=rule.prediction_cutoff,
                    insufficiency_reasons=rule.insufficiency_reasons,
                )
            if not predictions:
                prediction: DashboardPredictionSummary = UnavailableDashboardPrediction(
                    status="unavailable", reasons=["no_stored_prediction"]
                )
            elif predictions[0].status == "available":
                stored = predictions[0]
                prediction = AvailableDashboardPrediction(
                    status="available", probability=stored.probability,
                    prediction_cutoff=stored.prediction_cutoff,
                    generated_at=stored.generated_at, warnings=stored.warnings,
                )
            else:
                stored = predictions[0]
                prediction = UnavailableDashboardPrediction(
                    status="unavailable", prediction_cutoff=stored.prediction_cutoff,
                    generated_at=stored.generated_at, reasons=stored.reasons,
                    warnings=stored.warnings,
                )
            rows.append(DashboardPatient(patient=patient, current_rule=current_rule, prediction=prediction, latest_review_at=review_statuses.get(patient.patient_id)))
        sorted_rows = sorted(rows, key=_dashboard_sort_key)
        if self._disk_cache_enabled:
            self._store_dashboard_disk_cache(bounded_limit, sorted_rows)
            if refresh:
                self._clear_patient_disk_cache()
        self._dashboard_cache[bounded_limit] = (
            now + DASHBOARD_CACHE_TTL_SECONDS,
            tuple(row.model_copy(deep=True) for row in sorted_rows),
        )
        return sorted_rows

    @staticmethod
    def _dashboard_cache_path(limit: int) -> Path:
        return Path(__file__).resolve().parents[1] / ".cache" / f"dashboard-{limit}.json"

    def _load_dashboard_disk_cache(self, limit: int) -> list[DashboardPatient] | None:
        path = self._dashboard_cache_path(limit)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [DashboardPatient.model_validate(item) for item in payload["rows"]]
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _store_dashboard_disk_cache(self, limit: int, rows: list[DashboardPatient]) -> None:
        path = self._dashboard_cache_path(limit)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        payload = {
            "synced_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "rows": [row.model_dump(mode="json") for row in rows],
        }
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def _patient_cache_path(patient_id: str, suffix: str) -> Path:
        return Path(__file__).resolve().parents[1] / ".cache" / f"patient-{patient_id}-{suffix}.json"

    @staticmethod
    def _read_cache_json(path: Path) -> object | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _write_cache_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, path)

    def _clear_patient_disk_cache(self) -> None:
        cache_dir = Path(__file__).resolve().parents[1] / ".cache"
        if not cache_dir.exists():
            return
        for path in cache_dir.glob("patient-*.json"):
            path.unlink(missing_ok=True)

    def get_patient(self, patient_id: str, event_limit: int = 100) -> PatientDetail | None:
        """Read one active owned root and its independent EHR and IoT streams."""
        if not _PATIENT_ID.fullmatch(patient_id):
            raise ValueError("patient identifier must be a stable TwinBean identifier")
        cache_path = self._patient_cache_path(patient_id, f"detail-{event_limit}")
        cached = self._read_cache_json(cache_path) if self._disk_cache_enabled else None
        if cached is not None:
            return PatientDetail.model_validate(cached)
        active = self._load_active_cohort()
        if active is None:
            return None
        detail = self._get_patient_for_active(active, patient_id, event_limit)
        if detail is not None and self._disk_cache_enabled:
            self._write_cache_json(cache_path, detail.model_dump(mode="json"))
        return detail

    def _load_review_statuses(self) -> dict[str, datetime]:
        client = getattr(self, "_client", None)
        if client is None:
            return {}
        snapshots = client.collection("twinbean_doctor_reviews").stream(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
        statuses: dict[str, datetime] = {}
        for snapshot in snapshots:
            payload = snapshot.to_dict() or {}
            patient_id = payload.get("patient_id")
            latest_review_at = payload.get("latest_review_at")
            if isinstance(patient_id, str) and isinstance(latest_review_at, datetime):
                statuses[patient_id] = latest_review_at
        return statuses

    def list_review_notes(self, patient_id: str, limit: int = 20) -> list[ReviewNote]:
        if not self._is_known_patient(patient_id):
            return []
        snapshots = self._client.document(f"twinbean_doctor_reviews/{patient_id}").collection("notes").order_by("created_at").limit(min(max(limit, 1), 50)).stream(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
        notes = [ReviewNote.model_validate(snapshot.to_dict() or {}) for snapshot in snapshots]
        return list(reversed(notes))

    def create_review_note(self, patient_id: str, author_uid: str, text: str) -> ReviewNote | None:
        if not self._is_known_patient(patient_id):
            return None
        note = ReviewNote(note_id=f"note-{uuid.uuid4().hex}", patient_id=patient_id, author_uid=author_uid, text=text, created_at=datetime.now(UTC))
        batch = self._client.batch()
        review_document = self._client.document(f"twinbean_doctor_reviews/{patient_id}")
        document = review_document.collection("notes").document(note.note_id)
        batch.set(review_document, {"patient_id": patient_id, "latest_review_at": note.created_at, "latest_reviewer_uid": author_uid})
        batch.set(document, note.model_dump(mode="python"))
        batch.commit()
        self._mark_patient_reviewed(patient_id, note.created_at)
        return note

    def _mark_patient_reviewed(self, patient_id: str, reviewed_at: datetime) -> None:
        for limit, (expires_at, rows) in list(self._dashboard_cache.items()):
            updated = tuple(row.model_copy(update={"latest_review_at": reviewed_at}) if row.patient.patient_id == patient_id else row for row in rows)
            self._dashboard_cache[limit] = (expires_at, updated)
        if not self._disk_cache_enabled:
            return
        cache_dir = Path(__file__).resolve().parents[1] / ".cache"
        for path in cache_dir.glob("dashboard-*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                rows = [DashboardPatient.model_validate(item) for item in payload["rows"]]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            changed = False
            for index, row in enumerate(rows):
                if row.patient.patient_id == patient_id:
                    rows[index] = row.model_copy(update={"latest_review_at": reviewed_at})
                    changed = True
            if changed:
                self._store_dashboard_disk_cache(int(path.stem.split("-")[-1]), rows)

    def _is_known_patient(self, patient_id: str) -> bool:
        if not _PATIENT_ID.fullmatch(patient_id):
            return False
        if self._disk_cache_enabled:
            cache_dir = Path(__file__).resolve().parents[1] / ".cache"
            for path in cache_dir.glob(f"patient-{patient_id}-detail-*.json"):
                cached = self._read_cache_json(path)
                if cached is not None and PatientDetail.model_validate(cached).patient.patient_id == patient_id:
                    return True
        active = self._load_active_cohort_descriptor()
        return active is not None and self._get_patient_for_active(active, patient_id, 1) is not None

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
        from .prediction_service import ClinicalResultEnvelope

        validated_envelope = ClinicalResultEnvelope.model_validate(envelope)
        if (
            validated_envelope.clinical_rule.prediction_cutoff
            != validated_envelope.prediction.prediction_cutoff
        ):
            raise ValueError("clinical rule and prediction must share one cutoff")
        active = self._load_active_cohort()
        if active is None or (
            active.cohort_id,
            active.manifest_checksum,
            active.generator_version,
            active.seed,
        ) != (
            context.cohort_id,
            context.manifest_checksum,
            context.generator_version,
            context.seed,
        ):
            raise ValueError("clinical context no longer belongs to the active immutable cohort")
        patient_id = context.patient.patient.patient_id
        owned_root = (
            self._cohort_document(active.cohort_id).collection("patients").document(patient_id)
            .get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
            .to_dict()
        )
        if owned_root is None or self._summary_from_data(owned_root, active).patient_id != patient_id:
            raise ValueError("clinical context patient no longer belongs to the active immutable cohort")
        rule_payload = validated_envelope.clinical_rule.model_dump(mode="json")
        prediction_payload = validated_envelope.prediction.model_dump(mode="json")
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
        rule_path = f"{patient_path}/clinical_rules/{result_id}"
        prediction_path = f"{patient_path}/aki_predictions/{result_id}"
        rule_reference = self._client.document(rule_path)
        prediction_reference = self._client.document(prediction_path)
        existing_rule = rule_reference.get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS).to_dict()
        existing_prediction = prediction_reference.get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS).to_dict()
        if existing_rule is not None or existing_prediction is not None:
            if existing_rule == rule_document and existing_prediction == prediction_document:
                return result_id
            raise ValueError("clinical result attempt conflicts with immutable prior evidence")
        batch = self._client.batch()
        batch.create(rule_reference, rule_document)
        batch.create(prediction_reference, prediction_document)
        batch.commit()
        self._dashboard_cache.clear()
        return result_id

    def get_existing_clinical_results(
        self, context: ClinicalContext, envelope: Any
    ) -> Any | None:
        """Return the immutable result for the envelope identity, if already stored."""
        from .prediction_service import ClinicalResultEnvelope

        validated_envelope = ClinicalResultEnvelope.model_validate(envelope)
        rule_payload = validated_envelope.clinical_rule.model_dump(mode="json")
        prediction_payload = validated_envelope.prediction.model_dump(mode="json")
        result_id = _clinical_result_id(context, rule_payload, prediction_payload)
        patient_id = context.patient.patient.patient_id
        patient_path = _patient_path(context.cohort_id, patient_id)
        rule_data = (
            self._client.document(f"{patient_path}/clinical_rules/{result_id}")
            .get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
            .to_dict()
        )
        prediction_data = (
            self._client.document(f"{patient_path}/aki_predictions/{result_id}")
            .get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
            .to_dict()
        )
        if rule_data is None and prediction_data is None:
            return None
        if rule_data is None or prediction_data is None:
            raise ValueError("clinical result identity has incomplete immutable evidence")

        active = self._load_active_cohort()
        if active is None or (
            active.cohort_id,
            active.manifest_checksum,
            active.generator_version,
            active.seed,
        ) != (
            context.cohort_id,
            context.manifest_checksum,
            context.generator_version,
            context.seed,
        ):
            raise ValueError("clinical context no longer belongs to the active immutable cohort")
        stored_rule = _clinical_result_response_payload(
            rule_data, active, patient_id, "clinical_rule"
        )
        stored_prediction = _clinical_result_response_payload(
            prediction_data, active, patient_id, "aki_prediction"
        )
        return ClinicalResultEnvelope.model_validate(
            {"clinical_rule": stored_rule, "prediction": stored_prediction}
        )

    def list_clinical_rules(self, patient_id: str, limit: int) -> list["ClinicalRuleResult"]:
        """Return only active-cohort current-rule documents, newest calculation first."""

        from .clinical_rules import ClinicalRuleResult
        cache_path = self._patient_cache_path(patient_id, f"rules-{limit}")
        cached = self._read_cache_json(cache_path) if self._disk_cache_enabled else None
        if isinstance(cached, list):
            return [ClinicalRuleResult.model_validate(payload) for payload in cached]
        results = [
            ClinicalRuleResult.model_validate(payload)
            for payload in self._list_clinical_result_payloads(
                patient_id, limit, "clinical_rules", "clinical_rule", "calculation_time"
            )
        ]
        if self._disk_cache_enabled:
            self._write_cache_json(cache_path, [result.model_dump(mode="json") for result in results])
        return results

    def list_aki_predictions(self, patient_id: str, limit: int) -> list[Any]:
        """Return only active-cohort future-prediction documents, newest generation first."""

        from .prediction_service import validate_aki_prediction_result
        cache_path = self._patient_cache_path(patient_id, f"predictions-{limit}")
        cached = self._read_cache_json(cache_path) if self._disk_cache_enabled else None
        if isinstance(cached, list):
            return [validate_aki_prediction_result(payload) for payload in cached]
        results = [
            validate_aki_prediction_result(payload)
            for payload in self._list_clinical_result_payloads(
                patient_id, limit, "aki_predictions", "aki_prediction", "generated_at"
            )
        ]
        if self._disk_cache_enabled:
            self._write_cache_json(cache_path, [result.model_dump(mode="json") for result in results])
        return results

    def _list_clinical_result_payloads(
        self,
        patient_id: str,
        limit: int,
        collection: str,
        result_type: str,
        order_field: str,
    ) -> list[dict[str, object]]:
        if not _PATIENT_ID.fullmatch(patient_id):
            raise ValueError("patient identifier must be a stable TwinBean identifier")
        active = self._load_active_cohort()
        if active is None:
            return []
        return self._list_clinical_result_payloads_for_active(
            active, patient_id, limit, collection, result_type, order_field
        )

    def _list_clinical_result_payloads_for_active(
        self,
        active: _ActiveCohort,
        patient_id: str,
        limit: int,
        collection: str,
        result_type: str,
        order_field: str,
    ) -> list[dict[str, object]]:
        bounded_limit = min(max(limit, 1), MAX_CLINICAL_RESULT_RECORDS)
        patient_document = self._cohort_document(active.cohort_id).collection("patients").document(patient_id)
        snapshots = (
            patient_document.collection(collection)
            .order_by(order_field, direction="DESCENDING")
            .limit(bounded_limit)
            .stream(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS)
        )
        return [
            _clinical_result_response_payload(snapshot.to_dict() or {}, active, patient_id, result_type)
            for snapshot in snapshots
        ]

    def _get_patient_for_active(
        self, active: _ActiveCohort, patient_id: str, event_limit: int
    ) -> PatientDetail | None:
        document = self._cohort_document(active.cohort_id).collection("patients").document(patient_id)
        root_data = document.get(retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS).to_dict()
        if root_data is None:
            return None
        patient = self._summary_from_data(root_data, active)
        bounded_limit = min(max(event_limit, 1), MAX_HISTORY_RECORDS)
        ehr_events = document.collection("ehr_events").order_by("event_time").limit(bounded_limit).stream(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        )
        iot_observations = document.collection("iot_observations").order_by("observed_at").limit(bounded_limit).stream(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        )
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
        self._dashboard_cache.clear()
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
        pointer = self._client.document(ACTIVE_COHORT_PATH).get(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        ).to_dict()
        if pointer is None:
            return None
        active = _active_from_data(pointer)
        staged = self._validate_staged_cohort(active.cohort_id)
        if staged != active:
            raise ValueError("active cohort pointer does not exactly match its validated cohort")
        return active

    def _load_active_cohort_descriptor(self) -> _ActiveCohort | None:
        """Verify the activated immutable descriptor without rescanning the full cohort."""
        pointer = self._client.document(ACTIVE_COHORT_PATH).get(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        ).to_dict()
        if pointer is None:
            return None
        active = _active_from_data(pointer)
        descriptor = self._cohort_document(active.cohort_id).get(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        ).to_dict()
        if _active_from_data(descriptor or {}) != active:
            raise ValueError("active cohort pointer does not exactly match its validated cohort")
        return active

    def _validate_staged_cohort(self, cohort_id: str) -> _ActiveCohort:
        if not _COHORT_ID.fullmatch(cohort_id):
            raise ValueError("cohort identifier is not a TwinBean immutable version")
        descriptor = self._cohort_document(cohort_id).get(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        ).to_dict()
        active = _active_from_data(descriptor or {})
        if active.cohort_id != cohort_id:
            raise ValueError("staged cohort descriptor ownership does not match its path")
        manifest: list[tuple[str, dict[str, object]]] = []
        patient_snapshots = self._cohort_document(cohort_id).collection("patients").stream(
            retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
        )
        patient_count = ehr_count = iot_count = 0
        for root_snapshot in patient_snapshots:
            root_data = root_snapshot.to_dict() or {}
            patient = self._summary_from_data(root_data, active)
            _require_snapshot_id(root_snapshot, patient.patient_id)
            patient_count += 1
            root_path = _patient_path(cohort_id, patient.patient_id)
            manifest.append((root_path, dict(root_data)))
            document = self._client.document(root_path)
            for snapshot in document.collection("ehr_events").stream(
                retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
            ):
                data = snapshot.to_dict() or {}
                event = self._ehr_event_from_data(data, active, patient.patient_id)
                _require_snapshot_id(snapshot, event.event_id)
                ehr_count += 1
                manifest.append((f"{root_path}/ehr_events/{event.event_id}", dict(data)))
            for snapshot in document.collection("iot_observations").stream(
                retry=_FIRESTORE_READ_RETRY, timeout=FIRESTORE_READ_TIMEOUT_SECONDS
            ):
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
        return PatientSummary(
            patient_id=patient_id,
            display_name=display_name,
            age=age,
            sex=str(data["sex"]) if data.get("sex") is not None else None,
            ckd_stage=stage,
            ckd_context=str(data["ckd_context"]) if data.get("ckd_context") is not None else None,
        )

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


def _dashboard_sort_key(row: DashboardPatient) -> tuple[int, float, str, str]:
    if row.prediction.status == "available":
        return (0, -row.prediction.probability, row.patient.display_name.casefold(), row.patient.patient_id)
    return (1, 0.0, row.patient.display_name.casefold(), row.patient.patient_id)


def _patient_path(cohort_id: str, patient_id: str) -> str:
    return f"{_cohort_path(cohort_id)}/patients/{patient_id}"


def _clinical_result_id(
    context: ClinicalContext,
    rule_payload: Mapping[str, object],
    prediction_payload: Mapping[str, object],
) -> str:
    identity = {
        "cohort_id": context.cohort_id,
        "patient_id": context.patient.patient.patient_id,
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


_CLINICAL_RESULT_METADATA_FIELDS = frozenset(
    {
        "result_id",
        "result_type",
        "patient_id",
        "cohort_id",
        "manifest_checksum",
        "generator_version",
        "seed",
        "synthetic",
        "data_classification",
        "source",
    }
)


def _clinical_result_response_payload(
    payload: Mapping[str, object],
    active: _ActiveCohort,
    patient_id: str,
    result_type: str,
) -> dict[str, object]:
    _validate_clinical_result_payload(payload, result_type)
    if (
        payload.get("patient_id") != patient_id
        or payload.get("cohort_id") != active.cohort_id
        or payload.get("manifest_checksum") != active.manifest_checksum
        or payload.get("generator_version") != active.generator_version
        or payload.get("seed") != active.seed
    ):
        raise ValueError("clinical result does not belong to the active patient context")
    return {key: value for key, value in payload.items() if key not in _CLINICAL_RESULT_METADATA_FIELDS}


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
