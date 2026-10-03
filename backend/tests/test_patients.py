from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.patients import PatientRepository
from app.synthetic_data import generate_cohort


TIME_BASIS = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


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
            return type(
                "Result",
                (),
                {
                    "patient_count": 1,
                    "ehr_event_count": len(cohort.ehr_events),
                    "iot_observation_count": len(cohort.iot_observations),
                    "manifest_checksum": hashlib.sha256(b"manifest").hexdigest(),
                },
            )()

    monkeypatch.setattr(seed_synthetic_data, "generate_cohort", lambda **kwargs: calls.setdefault("generator", kwargs) and cohort)
    monkeypatch.setattr(seed_synthetic_data.PatientRepository, "from_firestore", lambda: FakeRepository())

    seed_synthetic_data.main(
        [
            "--seed",
            "5",
            "--generator-version",
            "2026.1",
            "--time-basis",
            "2026-01-15T12:00:00Z",
            "--patient-count",
            "1",
        ]
    )

    output = capsys.readouterr().out
    assert calls["generator"] == {
        "seed": 5,
        "generator_version": "2026.1",
        "time_basis": TIME_BASIS,
        "patient_count": 1,
    }
    assert calls["cohort"] is cohort
    assert "seed=5" in output
    assert "version=2026.1" in output
    assert "patients=1" in output
    assert "manifest_checksum=" in output
    assert "token" not in output.lower()
    assert "credential" not in output.lower()


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--seed", "-1"], "seed"),
        (["--generator-version", ""], "generator-version"),
        (["--time-basis", "2026-01-15T12:00:00"], "UTC"),
        (["--patient-count", "0"], "patient-count"),
    ],
)
def test_seed_cli_rejects_invalid_explicit_inputs(
    arguments: list[str],
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import seed_synthetic_data

    with pytest.raises(SystemExit):
        seed_synthetic_data.main(arguments)

    assert message in capsys.readouterr().err
