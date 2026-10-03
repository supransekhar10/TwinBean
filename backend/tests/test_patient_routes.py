import sys

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.main import app
from app.patient_routes import get_patient_repository
from app.patients import PatientRepository


client = TestClient(app)


class FakeRepository:
    def __init__(self, summaries: list[dict[str, object]]) -> None:
        self.summaries = summaries
        self.limits: list[int] = []

    def list_patients(self, limit: int) -> list[dict[str, object]]:
        self.limits.append(limit)
        return self.summaries


@pytest.fixture
def fake_repository() -> FakeRepository:
    repository = FakeRepository(
        [
            {
                "patient_id": "synthetic-001",
                "display_name": "Synthetic Patient 001",
                "age": 64,
                "ckd_stage": "G3b",
            }
        ]
    )
    app.dependency_overrides[get_patient_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_doctor_can_list_typed_root_patient_summaries(
    monkeypatch: pytest.MonkeyPatch,
    fake_repository: FakeRepository,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    response = client.get(
        "/patients",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "patient_id": "synthetic-001",
            "display_name": "Synthetic Patient 001",
            "age": 64,
            "ckd_stage": "G3b",
        }
    ]
    assert fake_repository.limits == [100]
    assert "firebase_admin.firestore" not in sys.modules


class FakeSnapshot:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, object]:
        return self._data


class FakeCollection:
    def __init__(self) -> None:
        self.order_field: str | None = None
        self.limit_value: int | None = None

    def order_by(self, field: str) -> "FakeCollection":
        self.order_field = field
        return self

    def limit(self, value: int) -> "FakeCollection":
        self.limit_value = value
        return self

    def stream(self) -> list[FakeSnapshot]:
        return [
            FakeSnapshot(
                {
                    "patient_id": "synthetic-001",
                    "display_name": "Synthetic Patient 001",
                    "age": 64,
                    "ckd_stage": "G3b",
                    "ehr_events": [{"event_id": "must-not-serialize"}],
                    "iot_observations": [{"observation_id": "must-not-serialize"}],
                }
            )
        ]


class FakeClient:
    def __init__(self) -> None:
        self.collection_name: str | None = None
        self.collection_ref = FakeCollection()

    def collection(self, name: str) -> FakeCollection:
        self.collection_name = name
        return self.collection_ref


def test_repository_lists_only_bounded_ordered_root_summaries() -> None:
    client_boundary = FakeClient()

    summaries = PatientRepository(client_boundary).list_patients(500)

    assert client_boundary.collection_name == "patients"
    assert client_boundary.collection_ref.order_field == "patient_id"
    assert client_boundary.collection_ref.limit_value == 100
    assert [summary.model_dump() for summary in summaries] == [
        {
            "patient_id": "synthetic-001",
            "display_name": "Synthetic Patient 001",
            "age": 64,
            "ckd_stage": "G3b",
        }
    ]
