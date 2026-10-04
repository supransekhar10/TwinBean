from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app import prediction_service as prediction_service_module
from app.clinical_rules import ClinicalRuleResult
from app.main import app
from app.patient_routes import get_patient_repository, get_prediction_service
from app.patients import ClinicalContext, PatientDetail, PatientSummary
from app.prediction_service import ClinicalResultEnvelope, UnavailableAkiPrediction
from app.prediction_service import PredictionService
from app.synthetic_data import generate_cohort


PATIENT_ID = "tbp-0123456789abcdef0123456789abcdef"
CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
client = TestClient(app)


class FakePredictionService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime]] = []

    def generate(self, patient_id: str, prediction_cutoff: datetime) -> ClinicalResultEnvelope:
        self.calls.append((patient_id, prediction_cutoff))
        return ClinicalResultEnvelope(
            clinical_rule=ClinicalRuleResult(
                status="insufficient_creatinine_history",
                calculation_time=prediction_cutoff,
                prediction_cutoff=prediction_cutoff,
                evidence=[],
            ),
            prediction=UnavailableAkiPrediction(
                status="unavailable",
                outcome="new_aki_within_24h",
                prediction_cutoff=prediction_cutoff,
                generated_at=prediction_cutoff,
                reasons=["model_engine_unavailable"],
            ),
        )


@pytest.fixture
def prediction_service() -> FakePredictionService:
    service = FakePredictionService()
    app.dependency_overrides[get_prediction_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


def _request(headers: dict[str, str] | None = None) -> object:
    return client.post(
        f"/patients/{PATIENT_ID}/clinical-results",
        headers=headers,
        json={"prediction_cutoff": CUTOFF.isoformat().replace("+00:00", "Z")},
    )


def test_doctor_can_generate_separate_current_rule_and_unavailable_forecast(
    monkeypatch: pytest.MonkeyPatch,
    prediction_service: FakePredictionService,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    response = _request({"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"clinical_rule", "prediction"}
    assert payload["clinical_rule"]["scope"] == "creatinine-only"
    assert payload["prediction"]["status"] == "unavailable"
    assert payload["prediction"]["reasons"]
    assert "probability" not in payload["prediction"]
    assert "attributions" not in payload["prediction"]
    assert prediction_service.calls == [(PATIENT_ID, CUTOFF)]


def test_missing_token_never_runs_clinical_work(prediction_service: FakePredictionService) -> None:
    response = _request()
    assert response.status_code == 401
    assert prediction_service.calls == []


def test_non_doctor_token_never_runs_clinical_work(
    monkeypatch: pytest.MonkeyPatch, prediction_service: FakePredictionService
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "research-user", "role": "researcher"},
    )

    response = _request({"Authorization": "Bearer valid-token"})

    assert response.status_code == 403
    assert prediction_service.calls == []


def test_invalid_token_never_runs_clinical_work(
    monkeypatch: pytest.MonkeyPatch, prediction_service: FakePredictionService
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: (_ for _ in ()).throw(ValueError("invalid")),
    )

    response = _request({"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert prediction_service.calls == []


def test_invalid_identifier_and_naive_cutoff_are_rejected_before_clinical_work(
    monkeypatch: pytest.MonkeyPatch, prediction_service: FakePredictionService
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    bad_identifier = client.post(
        "/patients/not-a-stable-id/clinical-results",
        headers={"Authorization": "Bearer valid-token"},
        json={"prediction_cutoff": CUTOFF.isoformat().replace("+00:00", "Z")},
    )
    naive_cutoff = client.post(
        f"/patients/{PATIENT_ID}/clinical-results",
        headers={"Authorization": "Bearer valid-token"},
        json={"prediction_cutoff": "2026-01-15T12:00:00"},
    )

    assert bad_identifier.status_code == 422
    assert naive_cutoff.status_code == 422
    assert prediction_service.calls == []


def test_missing_patient_returns_typed_404_after_authorization(
    monkeypatch: pytest.MonkeyPatch, prediction_service: FakePredictionService
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )
    prediction_service.generate = lambda _patient_id, _cutoff: None  # type: ignore[method-assign]

    response = _request({"Authorization": "Bearer valid-token"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found."}


def test_service_writes_one_separate_rule_and_prediction_envelope() -> None:
    class RecordingRepository:
        def __init__(self) -> None:
            self.writes: list[tuple[ClinicalContext, ClinicalResultEnvelope]] = []

        def get_clinical_context(self, patient_id: str) -> ClinicalContext:
            assert patient_id == PATIENT_ID
            return ClinicalContext(
                cohort_id="cohort-0123456789abcdef01234567",
                manifest_checksum="a" * 64,
                generator_version="2026.1",
                seed=7,
                patient=PatientDetail(
                    patient=PatientSummary(
                        patient_id=PATIENT_ID,
                        display_name="Synthetic CKD Patient",
                        age=64,
                        ckd_stage="G3b",
                    ),
                    ehr_history=[],
                    iot_observations=[],
                ),
            )

        def write_clinical_results(
            self, context: ClinicalContext, envelope: ClinicalResultEnvelope
        ) -> str:
            self.writes.append((context, envelope))
            return "clinical-test"

    repository = RecordingRepository()
    result = PredictionService(repository).generate(PATIENT_ID, CUTOFF)  # type: ignore[arg-type]

    assert result is not None
    assert len(repository.writes) == 1
    _, persisted = repository.writes[0]
    assert persisted.clinical_rule.scope == "creatinine-only"
    assert persisted.prediction.status == "unavailable"


def test_verified_engine_returns_a_complete_released_bundle_forecast() -> None:
    """A valid active synthetic context must use the released XGBoost/SHAP path."""

    cohort = generate_cohort(31, "2026.1", CUTOFF, patient_count=1)
    patient = cohort.patients[0]
    context = ClinicalContext(
        cohort_id="cohort-0123456789abcdef01234567",
        manifest_checksum="a" * 64,
        generator_version=cohort.provenance.generator_version,
        seed=cohort.provenance.seed,
        patient=PatientDetail(
            patient=PatientSummary(
                patient_id=patient.patient_id,
                display_name=patient.display_name,
                age=patient.age,
                ckd_stage=patient.ckd_stage,
            ),
            ehr_history=[event for event in cohort.ehr_events if event.patient_id == patient.patient_id],
            iot_observations=[
                observation
                for observation in cohort.iot_observations
                if observation.patient_id == patient.patient_id
            ],
        ),
    )

    engine_type = getattr(prediction_service_module, "VerifiedPredictionEngine", None)
    assert engine_type is not None
    result = engine_type().predict(context, CUTOFF)

    assert result.status == "available"
    assert result.outcome == "new_aki_within_24h"
    assert result.probability is not None
    assert result.attributions
    assert result.prediction_cutoff == CUTOFF
    assert all(item.semantics == "model influence in raw-margin/log-odds space; not causal" for item in result.attributions)
    assert all(item.expected_value == result.attributions[0].expected_value for item in result.attributions)
    assert all(item.expected_value == item.expected_value for item in result.attributions)
    assert all(item.expected_value is not None for item in result.attributions)


def test_doctor_can_read_separate_bounded_rule_and_prediction_histories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ResultRepository:
        def __init__(self) -> None:
            self.rule_calls: list[tuple[str, int]] = []
            self.prediction_calls: list[tuple[str, int]] = []

        def list_clinical_rules(self, patient_id: str, limit: int) -> list[ClinicalRuleResult]:
            self.rule_calls.append((patient_id, limit))
            return [
                ClinicalRuleResult(
                    status="insufficient_creatinine_history",
                    calculation_time=CUTOFF,
                    prediction_cutoff=CUTOFF,
                    evidence=[],
                )
            ]

        def list_aki_predictions(self, patient_id: str, limit: int) -> list[UnavailableAkiPrediction]:
            self.prediction_calls.append((patient_id, limit))
            return [
                UnavailableAkiPrediction(
                    status="unavailable",
                    outcome="new_aki_within_24h",
                    prediction_cutoff=CUTOFF,
                    generated_at=CUTOFF,
                    reasons=["missing_creatinine_history"],
                )
            ]

    repository = ResultRepository()
    app.dependency_overrides[get_patient_repository] = lambda: repository
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )
    headers = {"Authorization": "Bearer valid-token"}
    try:
        rules = client.get(f"/patients/{PATIENT_ID}/clinical-rules?limit=1", headers=headers)
        predictions = client.get(f"/patients/{PATIENT_ID}/aki-predictions?limit=1", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert rules.status_code == 200
    assert predictions.status_code == 200
    assert rules.json()[0]["status"] == "insufficient_creatinine_history"
    assert "probability" not in rules.json()[0]
    assert predictions.json()[0]["status"] == "unavailable"
    assert "evidence" not in predictions.json()[0]
    assert repository.rule_calls == [(PATIENT_ID, 1)]
    assert repository.prediction_calls == [(PATIENT_ID, 1)]


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        (None, 401),
        ({"Authorization": "Bearer non-doctor"}, 403),
    ],
)
def test_denied_result_history_reads_never_invoke_the_repository(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str] | None,
    expected_status: int,
) -> None:
    class ForbiddenRepository:
        def list_clinical_rules(self, *_args: object) -> list[object]:
            raise AssertionError("repository read must follow require_doctor")

        def list_aki_predictions(self, *_args: object) -> list[object]:
            raise AssertionError("repository read must follow require_doctor")

    app.dependency_overrides[get_patient_repository] = lambda: ForbiddenRepository()
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "research-user", "role": "researcher"},
    )
    try:
        rules = client.get(f"/patients/{PATIENT_ID}/clinical-rules", headers=headers)
        predictions = client.get(f"/patients/{PATIENT_ID}/aki-predictions", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert rules.status_code == expected_status
    assert predictions.status_code == expected_status
