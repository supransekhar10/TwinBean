import sys
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.main import app
from app.patient_routes import get_patient_repository
from app.patients import PatientDetail, PatientRepository
from app.synthetic_data import generate_cohort


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


class ReviewRepository:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str]] = []

    def list_review_notes(self, patient_id: str, limit: int) -> list[dict[str, object]]:
        return [{"note_id": "note-" + "a" * 32, "patient_id": patient_id, "author_uid": "demo-doctor", "text": "Review hydration trend.", "created_at": "2026-10-06T10:00:00Z"}][:limit]

    def create_review_note(self, patient_id: str, author_uid: str, text: str) -> dict[str, object]:
        self.created.append((patient_id, author_uid, text))
        return {"note_id": "note-" + "b" * 32, "patient_id": patient_id, "author_uid": author_uid, "text": text, "created_at": "2026-10-06T10:01:00Z"}


def test_doctor_can_read_and_create_separate_review_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = ReviewRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    headers = {"Authorization": "Bearer valid-token"}
    try:
        listed = client.get(f"/patients/{DETAIL_PATIENT_ID}/review-notes", headers=headers)
        created = client.post(f"/patients/{DETAIL_PATIENT_ID}/review-notes", headers=headers, json={"text": "  Recheck synthetic creatinine trend.  "})
    finally:
        app.dependency_overrides.clear()
    assert listed.status_code == 200
    assert listed.json()[0]["text"] == "Review hydration trend."
    assert created.status_code == 201
    assert created.json()["text"] == "Recheck synthetic creatinine trend."
    assert repository.created == [(DETAIL_PATIENT_ID, "demo-doctor", "Recheck synthetic creatinine trend.")]


def test_review_note_rejects_non_doctor_and_blank_text(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = ReviewRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    headers = {"Authorization": "Bearer valid-token"}
    try:
        monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "assistant", "role": "assistant"})
        forbidden = client.post(f"/patients/{DETAIL_PATIENT_ID}/review-notes", headers=headers, json={"text": "note"})
        monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
        invalid = client.post(f"/patients/{DETAIL_PATIENT_ID}/review-notes", headers=headers, json={"text": "   "})
    finally:
        app.dependency_overrides.clear()
    assert forbidden.status_code == 403
    assert invalid.status_code == 422
    assert repository.created == []


class FakeSnapshot:
    def __init__(self, data: dict[str, object] | None, identifier: str | None = None) -> None:
        self._data = data
        self.id = identifier

    def to_dict(self) -> dict[str, object] | None:
        return self._data


class FakeCollection:
    def __init__(self, client: "FakeClient", path: str) -> None:
        self.client = client
        self.path = path
        self.order_field: str | None = None
        self.limit_value: int | None = None

    def document(self, identifier: str) -> "FakeDocument":
        return FakeDocument(self.client, f"{self.path}/{identifier}")

    def order_by(self, field: str) -> "FakeCollection":
        self.order_field = field
        return self

    def limit(self, value: int) -> "FakeCollection":
        self.limit_value = value
        return self

    def stream(self, **_kwargs: object) -> list[FakeSnapshot]:
        prefix = f"{self.path}/"
        depth = self.path.count("/") + 1
        documents = [(path, data) for path, data in self.client.documents.items() if path.startswith(prefix) and path.count("/") == depth]
        documents.sort(key=lambda item: str(item[1].get(self.order_field or "")))
        if self.limit_value is not None:
            documents = documents[: self.limit_value]
        return [FakeSnapshot(data, path.rsplit("/", maxsplit=1)[-1]) for path, data in documents]


class FakeDocument:
    def __init__(self, client: "FakeClient", path: str) -> None:
        self.client = client
        self.path = path

    def get(self, **_kwargs: object) -> FakeSnapshot:
        return FakeSnapshot(self.client.documents.get(self.path), self.path.rsplit("/", maxsplit=1)[-1])

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.client, f"{self.path}/{name}")


class FakeBatch:
    def __init__(self, client: "FakeClient") -> None:
        self.client = client
        self.calls: list[tuple[str, dict[str, object]]] = []

    def set(self, document: FakeDocument, payload: dict[str, object]) -> None:
        self.calls.append((document.path, dict(payload)))

    def commit(self) -> None:
        self.client.documents.update(self.calls)


class FakeClient:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}
        self.collection_paths: list[str] = []

    def document(self, path: str) -> FakeDocument:
        return FakeDocument(self, path)

    def collection(self, path: str) -> FakeCollection:
        return FakeCollection(self, path)

    def batch(self) -> FakeBatch:
        return FakeBatch(self)

    def transaction(self) -> FakeBatch:
        return FakeBatch(self)


def test_repository_lists_only_bounded_ordered_root_summaries() -> None:
    client_boundary = FakeClient()
    cohort = generate_cohort(31, "2026.1", datetime(2026, 1, 15, tzinfo=UTC), patient_count=2)
    result = PatientRepository(client_boundary).write_cohort(cohort)
    summaries = PatientRepository(client_boundary).list_patients(500)
    assert result.cohort_id in next(path for path in client_boundary.documents if path.endswith("/patients/" + cohort.patients[0].patient_id))
    assert [summary.patient_id for summary in summaries] == sorted(patient.patient_id for patient in cohort.patients)


def test_repository_persists_review_status_with_note() -> None:
    client_boundary = FakeClient()
    cohort = generate_cohort(41, "2026.1", datetime(2026, 1, 15, tzinfo=UTC), patient_count=1)
    repository = PatientRepository(client_boundary)
    repository.write_cohort(cohort)
    patient_id = cohort.patients[0].patient_id

    note = repository.create_review_note(patient_id, "demo-doctor", "Reviewed synthetic trend.")

    assert note is not None
    status_payload = client_boundary.documents[f"twinbean_doctor_reviews/{patient_id}"]
    assert status_payload["patient_id"] == patient_id
    assert status_payload["latest_review_at"] == note.created_at
    assert status_payload["latest_reviewer_uid"] == "demo-doctor"


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


class ReportRepository(DetailRouteRepository):
    def get_patient(self, patient_id: str, event_limit: int = 100) -> PatientDetail:
        return PatientDetail.model_validate(super().get_patient(patient_id, event_limit))

    def list_clinical_rules(self, _patient_id: str, _limit: int) -> list[object]:
        return []

    def list_aki_predictions(self, _patient_id: str, _limit: int) -> list[object]:
        return []

    def list_review_notes(self, _patient_id: str, _limit: int) -> list[object]:
        return []


def test_doctor_can_download_branded_patient_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = ReportRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "demo-doctor", "role": "doctor"})
    try:
        response = client.get(f"/patients/{DETAIL_PATIENT_ID}/report.pdf", headers={"Authorization": "Bearer valid-token"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000


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
