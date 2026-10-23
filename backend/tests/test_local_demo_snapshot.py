from __future__ import annotations

import json
from pathlib import Path

from app.patients import DashboardPatient, PatientDetail
from app.prediction_service import AvailableAkiPrediction, ShapAttribution, validate_aki_prediction_result
from scripts.build_local_demo_snapshot import build_snapshot


class _AvailableEngine:
    def predict(self, _context, prediction_cutoff):
        return AvailableAkiPrediction(
            status="available",
            outcome="new_aki_within_24h",
            probability=0.62,
            prediction_cutoff=prediction_cutoff,
            generated_at=prediction_cutoff,
            model_version="test-model-v1",
            feature_schema_version="test-schema-v1",
            freshness_policy_version="test-freshness-v1",
            warnings=[],
            attributions=[
                ShapAttribution(
                    feature="latest_creatinine_mg_dl",
                    value=1.8,
                    expected_value=0.0,
                    shap_margin=0.2,
                )
            ],
        )


class _AgeRiskEngine(_AvailableEngine):
    def predict(self, context, prediction_cutoff):
        prediction = super().predict(context, prediction_cutoff)
        return prediction.model_copy(update={"probability": context.patient.patient.age / 100})


def test_local_snapshot_is_complete_honest_and_replaceable(tmp_path: Path) -> None:
    assert build_snapshot(tmp_path, patient_count=3, prediction_engine=_AvailableEngine()) == 3

    dashboard = json.loads((tmp_path / "dashboard-100.json").read_text(encoding="utf-8"))
    rows = [DashboardPatient.model_validate(row) for row in dashboard["rows"]]
    assert dashboard["source"] == "local_deterministic_synthetic_model_snapshot"
    assert len(rows) == 3
    assert all(row.patient.display_name for row in rows)
    assert all(row.prediction.status == "available" for row in rows)
    assert all(row.prediction.probability == 0.62 for row in rows if row.prediction.status == "available")

    for row in rows:
        patient_id = row.patient.patient_id
        detail = PatientDetail.model_validate_json(
            (tmp_path / f"patient-{patient_id}-detail-100.json").read_text(encoding="utf-8")
        )
        predictions = json.loads(
            (tmp_path / f"patient-{patient_id}-predictions-1.json").read_text(encoding="utf-8")
        )
        assert detail.ehr_history
        assert detail.iot_observations
        prediction = validate_aki_prediction_result(predictions[0])
        assert prediction.status == "available"
        assert prediction.probability == 0.62
        assert len(prediction.attributions) == 1


def test_local_snapshot_orders_available_predictions_by_highest_risk(tmp_path: Path) -> None:
    build_snapshot(tmp_path, patient_count=6, prediction_engine=_AgeRiskEngine())

    dashboard = json.loads((tmp_path / "dashboard-100.json").read_text(encoding="utf-8"))
    rows = [DashboardPatient.model_validate(row) for row in dashboard["rows"]]
    probabilities = [
        row.prediction.probability for row in rows if row.prediction.status == "available"
    ]

    assert probabilities == sorted(probabilities, reverse=True)
