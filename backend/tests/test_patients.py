from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.patients import PatientRepository
from app.synthetic_data import generate_cohort


TIME_BASIS = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
DETAIL_PATIENT_ID = "tbp-0123456789abcdef0123456789abcdef"


class FakeBatch:
    def __init__(self) -> None:
        self.set_calls: list[tuple[str, dict[str, object]]] = []
        self.committed = False

    def set(self, document: str, payload: dict[str, object]) -> None:
        self.set_calls.append((document, payload))

    def commit(self) -> None:
        self.committed = True


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.batches: list[FakeBatch] = []
        self.document_paths: list[str] = []

    def document(self, path: str) -> str:
        self.document_paths.append(path)
        return path

    def batch(self) -> FakeBatch:
        batch = FakeBatch()
        self.batches.append(batch)
        return batch


def _manifest(client: FakeFirestoreClient) -> list[tuple[str, dict[str, object]]]:
    return [call for batch in client.batches for call in batch.set_calls]


def test_writer_uses_lean_roots_and_separate_owned_event_subcollections() -> None:
    cohort = generate_cohort(73, "2026.1", TIME_BASIS, patient_count=2)
    client = FakeFirestoreClient()

    result = PatientRepository(client).write_cohort(cohort)
    manifest = _manifest(client)
    patient_roots = [(path, payload) for path, payload in manifest if path.count("/") == 1]
    ehr_paths = [path for path, _ in manifest if "/ehr_events/" in path]
    iot_paths = [path for path, _ in manifest if "/iot_observations/" in path]

    assert result.patient_count == 2
    assert len(patient_roots) == 2
    assert len(ehr_paths) == len(cohort.ehr_events)
    assert len(iot_paths) == len(cohort.iot_observations)
    assert all(path.startswith("patients/tbp-") for path, _ in patient_roots)
    assert all(path.startswith("patients/tbp-") and path.endswith(event.event_id) for path, event in zip(ehr_paths, cohort.ehr_events, strict=True))
    assert all(path.startswith("patients/tbp-") and path.endswith(observation.observation_id) for path, observation in zip(iot_paths, cohort.iot_observations, strict=True))
    assert all("ehr_events" not in payload and "iot_observations" not in payload for _, payload in patient_roots)
    assert all(payload["synthetic"] is True for _, payload in manifest)
    assert all(batch.committed for batch in client.batches)


def test_same_cohort_reuses_ordered_set_only_manifest_and_checksum() -> None:
    cohort = generate_cohort(91, "2026.1", TIME_BASIS, patient_count=3)
    first_client = FakeFirestoreClient()
    second_client = FakeFirestoreClient()

    first = PatientRepository(first_client).write_cohort(cohort)
    second = PatientRepository(second_client).write_cohort(cohort)

    assert _manifest(first_client) == _manifest(second_client)
    assert first.manifest_checksum == second.manifest_checksum
    assert first.write_count == second.write_count
    assert all(len(batch.set_calls) <= 100 for batch in first_client.batches)
    assert not hasattr(FakeBatch, "delete")
    assert not hasattr(FakeBatch, "update")
    assert not hasattr(FakeBatch, "create")


def test_writer_rejects_unowned_or_non_synthetic_data_before_opening_batch() -> None:
    cohort = generate_cohort(13, "2026.1", TIME_BASIS, patient_count=1)
    non_synthetic_patient = replace(cohort.patients[0], synthetic=False)
    invalid = replace(cohort, patients=(non_synthetic_patient,))
    client = FakeFirestoreClient()

    with pytest.raises(ValueError, match="synthetic"):
        PatientRepository(client).write_cohort(invalid)

    assert client.batches == []
    assert client.document_paths == []


def test_writer_bounds_documents_and_batch_payload_before_write() -> None:
    cohort = generate_cohort(17, "2026.1", TIME_BASIS, patient_count=3)
    oversized_event = replace(cohort.ehr_events[0], data={"blob": "x" * (900 * 1024)})
    oversized = replace(cohort, ehr_events=(oversized_event, *cohort.ehr_events[1:]))
    client = FakeFirestoreClient()

    with pytest.raises(ValueError, match="900 KiB"):
        PatientRepository(client).write_cohort(oversized)

    assert client.batches == []
    assert client.document_paths == []

    bounded_client = FakeFirestoreClient()
    PatientRepository(bounded_client).write_cohort(cohort)
    assert all(len(batch.set_calls) <= 100 for batch in bounded_client.batches)
    assert all(sum(len(str(payload).encode("utf-8")) for _, payload in batch.set_calls) < 8 * 1024 * 1024 for batch in bounded_client.batches)


def test_seed_cli_invokes_generator_and_repository_once_without_sensitive_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import seed_synthetic_data

    cohort = generate_cohort(5, "2026.1", TIME_BASIS, patient_count=1)
    calls: dict[str, object] = {}

    class FakeRepository:
        def write_cohort(self, received_cohort: object) -> object:
            calls["cohort"] = received_cohort
            return type("Result", (), {"patient_count": 1, "ehr_event_count": len(cohort.ehr_events), "iot_observation_count": len(cohort.iot_observations), "manifest_checksum": hashlib.sha256(b"manifest").hexdigest()})()

    monkeypatch.setattr(seed_synthetic_data, "generate_cohort", lambda **kwargs: calls.setdefault("generator", kwargs) and cohort)
    monkeypatch.setattr(seed_synthetic_data.PatientRepository, "from_firestore", lambda: FakeRepository())

    seed_synthetic_data.main(["--seed", "5", "--generator-version", "2026.1", "--time-basis", "2026-01-15T12:00:00Z", "--patient-count", "1"])

    output = capsys.readouterr().out
    assert calls["generator"] == {"seed": 5, "generator_version": "2026.1", "time_basis": TIME_BASIS, "patient_count": 1}
    assert calls["cohort"] is cohort
    assert "seed=5" in output
    assert "version=2026.1" in output
    assert "patients=1" in output
    assert "manifest_checksum=" in output
    assert "token" not in output.lower()
    assert "credential" not in output.lower()


@pytest.mark.parametrize(("arguments", "message"), [(["--seed", "-1"], "seed"), (["--generator-version", ""], "generator-version"), (["--time-basis", "2026-01-15T12:00:00"], "UTC"), (["--patient-count", "0"], "patient-count")])
def test_seed_cli_rejects_invalid_explicit_inputs(arguments: list[str], message: str, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts import seed_synthetic_data

    with pytest.raises(SystemExit):
        seed_synthetic_data.main(arguments)

    assert message in capsys.readouterr().err


class DetailSnapshot:
    def __init__(self, data: dict[str, object] | None) -> None:
        self._data = data

    def to_dict(self) -> dict[str, object] | None:
        return self._data


class DetailCollection:
    def __init__(self, snapshots: list[DetailSnapshot]) -> None:
        self.snapshots = snapshots
        self.order_field: str | None = None
        self.limit_value: int | None = None

    def order_by(self, field: str) -> "DetailCollection":
        self.order_field = field
        return self

    def limit(self, value: int) -> "DetailCollection":
        self.limit_value = value
        return self

    def stream(self) -> list[DetailSnapshot]:
        return self.snapshots


class DetailDocument:
    def __init__(self, root: DetailSnapshot, collections: dict[str, DetailCollection]) -> None:
        self.root = root
        self.collections = collections
        self.collection_names: list[str] = []
        self.get_calls = 0

    def get(self) -> DetailSnapshot:
        self.get_calls += 1
        return self.root

    def collection(self, name: str) -> DetailCollection:
        self.collection_names.append(name)
        return self.collections[name]


class DetailClient:
    def __init__(self, document: DetailDocument) -> None:
        self.detail_document = document
        self.document_paths: list[str] = []

    def document(self, path: str) -> DetailDocument:
        self.document_paths.append(path)
        return self.detail_document


def test_repository_reads_distinct_bounded_ehr_and_iot_histories_without_snapshots() -> None:
    ehr = DetailCollection([DetailSnapshot({"event_id": "ehr-0123456789abcdef0123456789abcdef", "patient_id": DETAIL_PATIENT_ID, "event_type": "laboratory", "event_time": "2026-01-02T00:00:00Z", "data": {"test_name": "egfr", "value": 35.0}, "synthetic": True, "generator_version": "2026.1", "seed": 7, "source": "twinbean-synthetic-ehr"})])
    iot = DetailCollection([DetailSnapshot({"observation_id": "iot-0123456789abcdef0123456789abcdef", "patient_id": DETAIL_PATIENT_ID, "measurement_type": "weight_kg", "observed_at": "2026-01-03T00:00:00Z", "data": {"value": 72.4, "unit": "kg"}, "synthetic": True, "generator_version": "2026.1", "seed": 7, "source": "twinbean-simulated-iot"})])
    document = DetailDocument(DetailSnapshot({"patient_id": DETAIL_PATIENT_ID, "display_name": "Synthetic CKD Patient", "age": 64, "ckd_stage": "G3b"}), {"ehr_events": ehr, "iot_observations": iot})
    repository = PatientRepository(DetailClient(document))

    assert callable(getattr(repository, "get_patient", None))
    detail = repository.get_patient(DETAIL_PATIENT_ID, event_limit=999)

    assert document.get_calls == 1
    assert document.collection_names == ["ehr_events", "iot_observations"]
    assert ehr.order_field == "event_time"
    assert iot.order_field == "observed_at"
    assert ehr.limit_value == 500
    assert iot.limit_value == 500
    serialized = detail.model_dump(mode="json")
    assert set(serialized) == {"patient", "ehr_history", "iot_observations"}
    assert serialized["ehr_history"][0]["source"] == "twinbean-synthetic-ehr"
    assert serialized["iot_observations"][0]["source"] == "twinbean-simulated-iot"
    assert not any(isinstance(item, DetailSnapshot) for item in (*detail.ehr_history, *detail.iot_observations))



def _ehr_snapshot(event_id: str, event_time: str) -> DetailSnapshot:
    return DetailSnapshot(
        {
            "event_id": event_id,
            "patient_id": DETAIL_PATIENT_ID,
            "event_type": "laboratory",
            "event_time": event_time,
            "data": {"test_name": "egfr"},
            "synthetic": True,
            "generator_version": "2026.1",
            "seed": 7,
            "source": "twinbean-synthetic-ehr",
        }
    )


def _iot_snapshot(observation_id: str, observed_at: str) -> DetailSnapshot:
    return DetailSnapshot(
        {
            "observation_id": observation_id,
            "patient_id": DETAIL_PATIENT_ID,
            "measurement_type": "weight_kg",
            "observed_at": observed_at,
            "data": {"value": 72.4, "unit": "kg"},
            "synthetic": True,
            "generator_version": "2026.1",
            "seed": 7,
            "source": "twinbean-simulated-iot",
        }
    )


def test_missing_patient_root_skips_all_child_stream_queries() -> None:
    document = DetailDocument(
        DetailSnapshot(None),
        {"ehr_events": DetailCollection([]), "iot_observations": DetailCollection([])},
    )
    client = DetailClient(document)

    detail = PatientRepository(client).get_patient(DETAIL_PATIENT_ID)

    assert detail is None
    assert client.document_paths == [f"patients/{DETAIL_PATIENT_ID}"]
    assert document.get_calls == 1
    assert document.collection_names == []


def test_empty_ehr_stream_is_preserved_without_replacing_iot_observations() -> None:
    document = DetailDocument(
        DetailSnapshot(
            {
                "patient_id": DETAIL_PATIENT_ID,
                "display_name": "Synthetic CKD Patient",
                "age": 64,
                "ckd_stage": "G3b",
            }
        ),
        {
            "ehr_events": DetailCollection([]),
            "iot_observations": DetailCollection([_iot_snapshot("iot-newest", "2026-01-03T00:00:00Z")]),
        },
    )

    detail = PatientRepository(DetailClient(document)).get_patient(DETAIL_PATIENT_ID)

    assert detail is not None
    assert detail.ehr_history == []
    assert [item.observation_id for item in detail.iot_observations] == ["iot-newest"]


def test_repository_normalizes_each_stream_to_ascending_utc_timestamp_order() -> None:
    document = DetailDocument(
        DetailSnapshot(
            {
                "patient_id": DETAIL_PATIENT_ID,
                "display_name": "Synthetic CKD Patient",
                "age": 64,
                "ckd_stage": "G3b",
            }
        ),
        {
            "ehr_events": DetailCollection(
                [
                    _ehr_snapshot("ehr-later", "2026-01-03T00:00:00Z"),
                    _ehr_snapshot("ehr-earlier", "2026-01-01T00:00:00Z"),
                ]
            ),
            "iot_observations": DetailCollection(
                [
                    _iot_snapshot("iot-later", "2026-01-04T00:00:00Z"),
                    _iot_snapshot("iot-earlier", "2026-01-02T00:00:00Z"),
                ]
            ),
        },
    )

    detail = PatientRepository(DetailClient(document)).get_patient(DETAIL_PATIENT_ID)

    assert detail is not None
    assert [item.event_id for item in detail.ehr_history] == ["ehr-earlier", "ehr-later"]
    assert [item.observation_id for item in detail.iot_observations] == ["iot-earlier", "iot-later"]
