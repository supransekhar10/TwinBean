from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.clinical_rules import ClinicalRuleResult
from app.main import app
from app.patient_routes import get_patient_repository
from app.patients import PatientRepository, PatientSummary
from app.prediction_service import AvailableAkiPrediction, UnavailableAkiPrediction


client = TestClient(app)
CUTOFF = datetime(2026, 1, 15, 12, tzinfo=UTC)


class ProjectionRepository(PatientRepository):
    def __init__(self) -> None:
        self.patient_limit: int | None = None
        self.rule_calls: list[tuple[str, int]] = []
        self.prediction_calls: list[tuple[str, int]] = []
        self.patients = [
            PatientSummary(patient_id="tbp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", display_name="Zulu", age=71, ckd_stage="G4"),
            PatientSummary(patient_id="tbp-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", display_name="alpha", age=63, ckd_stage="G3b"),
            PatientSummary(patient_id="tbp-cccccccccccccccccccccccccccccccc", display_name="Beta", age=58, ckd_stage="G3a"),
        ]

    def list_patients(self, limit: int) -> list[PatientSummary]:
        self.patient_limit = limit
        return self.patients[:limit]

    def list_clinical_rules(self, patient_id: str, limit: int) -> list[ClinicalRuleResult]:
        self.rule_calls.append((patient_id, limit))
        if patient_id.endswith("a" * 32):
            return []
        return [
            ClinicalRuleResult(
                status="insufficient_creatinine_history",
                calculation_time=CUTOFF,
                prediction_cutoff=CUTOFF,
                evidence=[],
                insufficiency_reasons=["no_valid_creatinine_evidence"],
            )
        ]

    def list_aki_predictions(self, patient_id: str, limit: int) -> list[AvailableAkiPrediction | UnavailableAkiPrediction]:
        self.prediction_calls.append((patient_id, limit))
        if patient_id.endswith("a" * 32):
            return [
                AvailableAkiPrediction(
                    status="available",
                    outcome="new_aki_within_24h",
                    probability=0.82,
                    prediction_cutoff=CUTOFF,
                    generated_at=CUTOFF,
                    model_version="aki-24h-test",
                    feature_schema_version="aki-combined-v1",
                    freshness_policy_version="freshness-v1",
                    warnings=["iot_data_stale"],
                    attributions=[],
                )
            ]
        if patient_id.endswith("b" * 32):
            return [
                UnavailableAkiPrediction(
                    status="unavailable",
                    outcome="new_aki_within_24h",
                    prediction_cutoff=CUTOFF,
                    generated_at=CUTOFF,
                    reasons=["missing_iot_window"],
                    warnings=["iot_data_missing"],
                )
            ]
        return []


def test_repository_builds_bounded_sorted_separate_dashboard_projection() -> None:
    repository = ProjectionRepository()

    rows = repository.list_dashboard_patients(500)

    assert repository.patient_limit == 100
    assert repository.rule_calls == [(patient.patient_id, 1) for patient in repository.patients]
    assert repository.prediction_calls == [(patient.patient_id, 1) for patient in repository.patients]
    assert [row.patient.display_name for row in rows] == ["Zulu", "alpha", "Beta"]
    assert rows[0].prediction.status == "available"
    assert rows[0].prediction.probability == 0.82
    assert rows[0].current_rule is None
    assert rows[1].prediction.status == "unavailable"
    assert rows[1].prediction.reasons == ["missing_iot_window"]
    assert rows[1].current_rule is not None
    assert rows[1].current_rule.status == "insufficient_creatinine_history"
    assert rows[2].prediction.status == "unavailable"
    assert rows[2].prediction.reasons == ["no_stored_prediction"]
    assert "probability" not in rows[2].prediction.model_dump()


class RouteRepository:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def list_dashboard_patients(self, limit: int) -> list[object]:
        self.calls.append(limit)
        return ProjectionRepository().list_dashboard_patients(limit)


@pytest.fixture
def route_repository() -> RouteRepository:
    repository = RouteRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_doctor_can_read_dashboard_without_generating_predictions(monkeypatch: pytest.MonkeyPatch, route_repository: RouteRepository) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "doctor", "role": "doctor"})
    response = client.get("/dashboard/patients?limit=3", headers={"Authorization": "Bearer valid"})

    assert response.status_code == 200
    assert route_repository.calls == [3]
    payload = response.json()
    assert [row["patient"]["display_name"] for row in payload] == ["Zulu", "alpha", "Beta"]
    assert set(payload[0]) == {"patient", "current_rule", "prediction"}
    assert payload[0]["prediction"]["generated_at"] == CUTOFF.isoformat().replace("+00:00", "Z")
    assert payload[0]["prediction"]["warnings"] == ["iot_data_stale"]
    assert "probability" not in payload[2]["prediction"]


@pytest.mark.parametrize(
    ("headers", "claims", "expected_status"),
    [
        (None, None, 401),
        ({"Authorization": "Bearer valid"}, {"uid": "researcher", "role": "researcher"}, 403),
    ],
)
def test_dashboard_requires_exact_doctor_role(
    monkeypatch: pytest.MonkeyPatch,
    route_repository: RouteRepository,
    headers: dict[str, str] | None,
    claims: dict[str, str] | None,
    expected_status: int,
) -> None:
    if claims is not None:
        monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: claims)
    response = client.get("/dashboard/patients", headers=headers)
    assert response.status_code == expected_status
    assert route_repository.calls == []


@pytest.mark.parametrize("limit", [0, 101])
def test_dashboard_rejects_unbounded_limit(monkeypatch: pytest.MonkeyPatch, route_repository: RouteRepository, limit: int) -> None:
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "doctor", "role": "doctor"})
    response = client.get(f"/dashboard/patients?limit={limit}", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 422
    assert route_repository.calls == []


def test_dashboard_returns_honest_empty_cohort(monkeypatch: pytest.MonkeyPatch, route_repository: RouteRepository) -> None:
    route_repository.list_dashboard_patients = lambda limit: []  # type: ignore[method-assign]
    monkeypatch.setattr(auth_module, "verify_firebase_token", lambda _token: {"uid": "doctor", "role": "doctor"})
    response = client.get("/dashboard/patients", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 200
    assert response.json() == []
