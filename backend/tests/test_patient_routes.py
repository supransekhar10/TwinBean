import sys

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.main import app
from app.patient_routes import get_patient_repository
from app.patients import PatientRepository


client = TestClient(app)
DETAIL_PATIENT_ID = "tbp-0123456789abcdef0123456789abcdef"


class FakeRepository:
    def __init__(self, summaries: list[dict[str, object]]) -> None:
        self.summaries = summaries
        self.limits: list[int] = []

    def list_patients(self, limit: int) -> list[dict[str, object]]:
        self.limits.append(limit)
        return self.summaries


@pytest.fixture
def fake_repository() -> FakeRepository:
    repository = FakeRepository([{"patient_id": "synthetic-001", "display_name": "Synthetic Patient 001", "age": 64, "ckd_stage": "G3b"}])
    app.dependency_overrides[get_patient_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_doctor_can_list_typed_root_patient_summaries(monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    response = client.get("/patients", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json() == [{"patient_id": "synthetic-001", "display_name": "Synthetic Patient 001", "age": 64, "ckd_stage": "G3b"}]
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
        return [FakeSnapshot({"patient_id": "synthetic-001", "display_name": "Synthetic Patient 001", "age": 64, "ckd_stage": "G3b", "ehr_events": [{"event_id": "must-not-serialize"}], "iot_observations": [{"observation_id": "must-not-serialize"}]})]


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
    assert [summary.model_dump() for summary in summaries] == [{"patient_id": "synthetic-001", "display_name": "Synthetic Patient 001", "age": 64, "ckd_stage": "G3b"}]


def test_missing_token_is_unauthorized_without_repository_access(fake_repository: FakeRepository) -> None:
    response = client.get("/patients")
    assert response.status_code == 401
    assert fake_repository.limits == []


def test_invalid_token_is_unauthorized_without_repository_access(monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository) -> None:
    def reject(_token: str) -> dict[str, str]:
        raise ValueError("invalid")

    monkeypatch.setattr(auth_module, "verify_firebase_token", reject)
    response = client.get("/patients", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert fake_repository.limits == []


def test_non_doctor_is_forbidden_without_repository_access(monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "research-user", "role": "researcher"})
    response = client.get("/patients", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert fake_repository.limits == []


@pytest.mark.parametrize("limit", [0, 101])
def test_out_of_bounds_limit_is_rejected(monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository, limit: int) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    response = client.get(f"/patients?limit={limit}", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 422
    assert fake_repository.limits == []


def test_doctor_receives_an_honest_empty_patient_list(monkeypatch: pytest.MonkeyPatch, fake_repository: FakeRepository) -> None:
    fake_repository.summaries = []
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    response = client.get("/patients", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json() == []
    assert fake_repository.limits == [100]


class DetailRouteRepository:
    def __init__(self) -> None:
        self.patient_ids: list[str] = []

    def get_patient(self, patient_id: str, event_limit: int = 100) -> dict[str, object]:
        self.patient_ids.append(patient_id)
        return {"patient": {"patient_id": patient_id, "display_name": "Synthetic CKD Patient", "age": 64, "ckd_stage": "G3b"}, "ehr_history": [{"event_id": "ehr-0123456789abcdef0123456789abcdef", "patient_id": patient_id, "event_type": "laboratory", "event_time": "2026-01-02T00:00:00Z", "data": {"test_name": "egfr", "value": 35.0}, "synthetic": True, "generator_version": "2026.1", "seed": 7, "source": "twinbean-synthetic-ehr"}], "iot_observations": [{"observation_id": "iot-0123456789abcdef0123456789abcdef", "patient_id": patient_id, "measurement_type": "weight_kg", "observed_at": "2026-01-03T00:00:00Z", "data": {"value": 72.4, "unit": "kg"}, "synthetic": True, "generator_version": "2026.1", "seed": 7, "source": "twinbean-simulated-iot"}]}


@pytest.fixture
def detail_repository() -> DetailRouteRepository:
    repository = DetailRouteRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_doctor_can_read_separate_typed_patient_detail(monkeypatch: pytest.MonkeyPatch, detail_repository: DetailRouteRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    response = client.get(f"/patients/{DETAIL_PATIENT_ID}", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"patient", "ehr_history", "iot_observations"}
    assert "history" not in payload
    assert payload["ehr_history"][0]["source"] == "twinbean-synthetic-ehr"
    assert payload["iot_observations"][0]["source"] == "twinbean-simulated-iot"
    assert detail_repository.patient_ids == [DETAIL_PATIENT_ID]


def test_missing_detail_token_never_calls_repository(detail_repository: DetailRouteRepository) -> None:
    response = client.get(f"/patients/{DETAIL_PATIENT_ID}")
    assert response.status_code == 401
    assert detail_repository.patient_ids == []


def test_invalid_detail_token_never_calls_repository(monkeypatch: pytest.MonkeyPatch, detail_repository: DetailRouteRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: (_ for _ in ()).throw(ValueError("invalid")))
    response = client.get(f"/patients/{DETAIL_PATIENT_ID}", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert detail_repository.patient_ids == []


def test_non_doctor_detail_token_never_calls_repository(monkeypatch: pytest.MonkeyPatch, detail_repository: DetailRouteRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "research-user", "role": "researcher"})
    response = client.get(f"/patients/{DETAIL_PATIENT_ID}", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403
    assert detail_repository.patient_ids == []


def test_invalid_detail_identifier_is_rejected_before_lookup(monkeypatch: pytest.MonkeyPatch, detail_repository: DetailRouteRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    response = client.get("/patients/not-a-stable-id", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 422
    assert detail_repository.patient_ids == []



class MissingDetailRouteRepository(DetailRouteRepository):
    def get_patient(self, patient_id: str, event_limit: int = 100) -> None:
        self.patient_ids.append(patient_id)
        return None


def test_missing_detail_root_returns_404_without_storage_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MissingDetailRouteRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    try:
        response = client.get(
            f"/patients/{DETAIL_PATIENT_ID}",
            headers={"Authorization": "Bearer valid-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found."}
    assert repository.patient_ids == [DETAIL_PATIENT_ID]
