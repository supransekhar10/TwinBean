from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import pytest

from app.patients import ACTIVE_COHORT_PATH, PatientRepository
from app.clinical_rules import ClinicalRuleResult
from app.prediction_service import ClinicalResultEnvelope, UnavailableAkiPrediction
from app.synthetic_data import generate_cohort


TIME_BASIS = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


class Snapshot:
    def __init__(self, data: dict[str, object] | None, identifier: str | None = None) -> None:
        self._data = data
        self.id = identifier

    def to_dict(self) -> dict[str, object] | None:
        return None if self._data is None else dict(self._data)


class Document:
    def __init__(self, client: "MemoryFirestore", path: str) -> None:
        self.client, self.path = client, path

    def get(self) -> Snapshot:
        return Snapshot(self.client.documents.get(self.path), self.path.rsplit("/", maxsplit=1)[-1])

    def collection(self, name: str) -> "Collection":
        return Collection(self.client, f"{self.path}/{name}")


class Collection:
    def __init__(self, client: "MemoryFirestore", path: str) -> None:
        self.client, self.path = client, path
        self.order_field: str | None = None
        self.descending = False
        self.limit_value: int | None = None

    def document(self, identifier: str) -> Document:
        return Document(self.client, f"{self.path}/{identifier}")

    def order_by(self, field: str, direction: str | None = None) -> "Collection":
        self.order_field = field
        self.descending = direction == "DESCENDING"
        return self

    def limit(self, value: int) -> "Collection":
        self.limit_value = value
        return self

    def stream(self) -> list[Snapshot]:
        prefix = f"{self.path}/"
        depth = self.path.count("/") + 1
        records = [(path, data) for path, data in self.client.documents.items() if path.startswith(prefix) and path.count("/") == depth]
        records.sort(
            key=lambda item: (str(item[1].get(self.order_field or "")), item[0]),
            reverse=self.descending,
        )
        if self.limit_value is not None:
            records = records[: self.limit_value]
        return [Snapshot(data, path.rsplit("/", maxsplit=1)[-1]) for path, data in records]


class Batch:
    def __init__(self, client: "MemoryFirestore") -> None:
        self.client, self.set_calls = client, []

    def set(self, document: Document, payload: dict[str, object]) -> None:
        self.set_calls.append((document.path, dict(payload)))

    def create(self, document: Document, payload: dict[str, object]) -> None:
        if document.path in self.client.documents:
            raise RuntimeError("simulated document already exists")
        self.set(document, payload)

    def commit(self) -> None:
        self.client.batch_commits += 1
        if self.client.fail_batch == self.client.batch_commits:
            raise RuntimeError("simulated batch failure")
        for path, payload in self.set_calls:
            self.client.documents[path] = payload
        if self.client.corrupt_after_stage:
            for path, payload in self.set_calls:
                if "/ehr_events/" in path:
                    self.client.documents[path]["event_type"] = "tampered"
                    self.client.corrupt_after_stage = False
                    break


class Transaction(Batch):

    def commit(self) -> None:
        self.client.transaction_commits += 1
        if self.client.fail_transaction == self.client.transaction_commits:
            raise RuntimeError("simulated transaction failure")
        if self.client.fail_activation:
            raise RuntimeError("simulated activation failure")
        for path, payload in self.set_calls:
            self.client.documents[path] = payload


class MemoryFirestore:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}
        self.batch_commits = 0
        self.transaction_commits = 0
        self.fail_batch: int | None = None
        self.fail_transaction: int | None = None
        self.fail_activation = False
        self.corrupt_after_stage = False

    def document(self, path: str) -> Document:
        return Document(self, path)

    def batch(self) -> Batch:
        return Batch(self)

    def transaction(self) -> Transaction:
        return Transaction(self)


def _cohort(seed: int, count: int = 1):
    return generate_cohort(seed, "2026.1", TIME_BASIS, patient_count=count)


def _active(client: MemoryFirestore) -> dict[str, object]:
    return client.documents[ACTIVE_COHORT_PATH]


def _unavailable_envelope(cutoff: datetime) -> ClinicalResultEnvelope:
    return ClinicalResultEnvelope(
        clinical_rule=ClinicalRuleResult(
            status="insufficient_creatinine_history",
            calculation_time=cutoff,
            prediction_cutoff=cutoff,
            evidence=[],
        ),
        prediction=UnavailableAkiPrediction(
            status="unavailable",
            outcome="new_aki_within_24h",
            prediction_cutoff=cutoff,
            generated_at=cutoff,
            reasons=["model_engine_unavailable"],
        ),
    )


def test_writer_stages_only_versioned_owned_paths_then_publishes_one_pointer() -> None:
    client = MemoryFirestore()
    cohort = _cohort(73, 2)
    result = PatientRepository(client).write_cohort(cohort)

    assert result.cohort_id.startswith("cohort-")
    assert result.write_count == 2 + len(cohort.patients) + len(cohort.ehr_events) + len(cohort.iot_observations)
    assert set(client.documents) >= {ACTIVE_COHORT_PATH, f"twinbean_cohorts/{result.cohort_id}"}
    patient_paths = [path for path in client.documents if "/patients/" in path]
    assert patient_paths
    assert all(path.startswith(f"twinbean_cohorts/{result.cohort_id}/patients/tbp-") for path in patient_paths)
    assert all("/ehr_events/" in path or "/iot_observations/" in path or path.count("/") == 3 for path in patient_paths)
    assert _active(client)["cohort_id"] == result.cohort_id
    assert client.transaction_commits == 1


def test_same_inputs_produce_the_same_immutable_cohort_version_and_checksum() -> None:
    first, second = MemoryFirestore(), MemoryFirestore()
    one = PatientRepository(first).write_cohort(_cohort(91, 3))
    two = PatientRepository(second).write_cohort(_cohort(91, 3))

    assert (one.cohort_id, one.manifest_checksum) == (two.cohort_id, two.manifest_checksum)
    assert one.write_count == two.write_count


def test_mid_batch_failure_never_changes_previous_active_pointer() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    original = repository.write_cohort(_cohort(1, 1))
    client.fail_batch = client.batch_commits + 2

    with pytest.raises(RuntimeError, match="batch"):
        repository.write_cohort(_cohort(2, 3))

    assert _active(client)["cohort_id"] == original.cohort_id
    assert [item.patient_id for item in repository.list_patients(10)] == [original_patient.patient_id for original_patient in _cohort(1, 1).patients]


def test_validation_checksum_mismatch_never_publishes_staged_version() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    original = repository.write_cohort(_cohort(3))
    client.corrupt_after_stage = True

    with pytest.raises(ValueError, match="checksum"):
        repository.write_cohort(_cohort(4))

    assert _active(client)["cohort_id"] == original.cohort_id


def test_failed_activation_preserves_previous_pointer_after_valid_readback() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    original = repository.write_cohort(_cohort(5))
    client.fail_activation = True

    with pytest.raises(RuntimeError, match="activation"):
        repository.write_cohort(_cohort(6))

    assert _active(client)["cohort_id"] == original.cohort_id


def test_reads_resolve_only_the_active_cohort_and_ignore_foreign_roots() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    first = repository.write_cohort(_cohort(7))
    second = repository.write_cohort(_cohort(8))
    client.documents["patients/tbp-0123456789abcdef0123456789abcdef"] = {"synthetic": False}
    client.documents["foreign/patient"] = {"synthetic": False}

    summaries = repository.list_patients(100)

    assert first.cohort_id != second.cohort_id
    assert [summary.patient_id for summary in summaries] == [patient.patient_id for patient in _cohort(8).patients]


@pytest.mark.parametrize("field,value", [("synthetic", "false"), ("source", "foreign-source")])
def test_read_rejects_malformed_or_non_synthetic_active_records(field: str, value: object) -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    result = repository.write_cohort(_cohort(9))
    child_path = next(path for path in client.documents if path.startswith(f"twinbean_cohorts/{result.cohort_id}/patients/") and "/ehr_events/" in path)
    client.documents[child_path][field] = value

    with pytest.raises(ValueError, match="provenance"):
        repository.list_patients(100)


def test_read_rejects_non_utc_timestamp_in_the_active_cohort() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    result = repository.write_cohort(_cohort(12))
    child_path = next(path for path in client.documents if path.startswith(f"twinbean_cohorts/{result.cohort_id}/patients/") and "/ehr_events/" in path)
    client.documents[child_path]["event_time"] = "2026-01-01T00:00:00+05:30"

    with pytest.raises(ValueError, match="UTC"):
        repository.list_patients(100)


@pytest.mark.parametrize("field,value", [("patient_id", "tbp-ffffffffffffffffffffffffffffffff"), ("cohort_id", "cohort-ffffffffffffffffffffffff")])
def test_read_rejects_child_with_mismatched_parent_or_provenance(field: str, value: str) -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    result = repository.write_cohort(_cohort(10))
    patient_id = _cohort(10).patients[0].patient_id
    child_path = next(path for path in client.documents if "/iot_observations/" in path)
    client.documents[child_path][field] = value

    with pytest.raises(ValueError):
        repository.get_patient(patient_id)


def test_clinical_results_use_one_deterministic_id_in_separate_owned_paths() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    seeded = repository.write_cohort(_cohort(21))
    patient_id = _cohort(21).patients[0].patient_id
    context = repository.get_clinical_context(patient_id)
    assert context is not None
    cutoff = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    pointer_before = dict(_active(client))
    batch_commits_before = client.batch_commits

    first = repository.write_clinical_results(context, _unavailable_envelope(cutoff))
    second = repository.write_clinical_results(context, _unavailable_envelope(cutoff))

    conflicting = _unavailable_envelope(cutoff)
    conflicting.prediction.reasons = ["different_attempt_evidence"]
    documents_before_conflict = {path: dict(payload) for path, payload in client.documents.items()}

    with pytest.raises(ValueError, match="immutable prior evidence"):
        repository.write_clinical_results(context, conflicting)

    assert client.documents == documents_before_conflict

    assert first == second
    base = f"twinbean_cohorts/{seeded.cohort_id}/patients/{patient_id}"
    rule_path = f"{base}/clinical_rules/{first}"
    prediction_path = f"{base}/aki_predictions/{first}"
    assert set(client.documents[rule_path]) & {"probability", "attributions", "reasons", "outcome"} == set()
    assert set(client.documents[prediction_path]) & {"evidence", "scope", "limitation", "rule_version"} == set()
    assert client.documents[prediction_path]["status"] == "unavailable"
    assert _active(client) == pointer_before
    assert client.batch_commits == batch_commits_before + 1


def test_failed_clinical_result_transaction_leaves_all_existing_documents_unchanged() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    repository.write_cohort(_cohort(22))
    active = repository.write_cohort(_cohort(23))
    patient_id = _cohort(23).patients[0].patient_id
    context = repository.get_clinical_context(patient_id)
    assert context is not None
    client.documents["unrelated/canary"] = {"value": "untouched"}
    before = {path: dict(payload) for path, payload in client.documents.items()}
    client.fail_batch = client.batch_commits + 1

    with pytest.raises(RuntimeError, match="batch"):
        repository.write_clinical_results(
            context, _unavailable_envelope(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
        )

    assert client.documents == before
    assert _active(client)["cohort_id"] == active.cohort_id


def test_clinical_result_histories_are_distinct_bounded_and_newest_first() -> None:
    client = MemoryFirestore()
    repository = PatientRepository(client)
    repository.write_cohort(_cohort(24))
    patient_id = _cohort(24).patients[0].patient_id
    context = repository.get_clinical_context(patient_id)
    assert context is not None
    first_cutoff = datetime(2026, 1, 14, 12, 0, tzinfo=UTC)
    second_cutoff = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)

    repository.write_clinical_results(context, _unavailable_envelope(first_cutoff))
    repository.write_clinical_results(context, _unavailable_envelope(second_cutoff))

    rules = repository.list_clinical_rules(patient_id, 1)
    predictions = repository.list_aki_predictions(patient_id, 1)

    assert [rule.prediction_cutoff for rule in rules] == [second_cutoff]
    assert [prediction.prediction_cutoff for prediction in predictions] == [second_cutoff]
    assert "probability" not in rules[0].model_dump()
    assert "evidence" not in predictions[0].model_dump()


def test_cli_reports_only_non_sensitive_seed_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts import seed_synthetic_data

    cohort = _cohort(11)
    calls: dict[str, Any] = {}

    class FakeRepository:
        def write_cohort(self, received: object) -> object:
            calls["cohort"] = received
            return type("Result", (), {"patient_count": 1, "ehr_event_count": len(cohort.ehr_events), "iot_observation_count": len(cohort.iot_observations), "manifest_checksum": hashlib.sha256(b"manifest").hexdigest()})()

    monkeypatch.setattr(seed_synthetic_data, "generate_cohort", lambda **kwargs: calls.setdefault("generator", kwargs) and cohort)
    monkeypatch.setattr(seed_synthetic_data.PatientRepository, "from_firestore", lambda: FakeRepository())
    seed_synthetic_data.main(["--seed", "11", "--generator-version", "2026.1", "--time-basis", "2026-01-15T12:00:00Z", "--patient-count", "1"])

    output = capsys.readouterr().out
    assert calls["cohort"] is cohort
    assert "seed=11" in output and "manifest_checksum=" in output
    assert "token" not in output.lower() and "credential" not in output.lower()
