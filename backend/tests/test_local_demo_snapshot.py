from __future__ import annotations

import json
from pathlib import Path

from app.patients import DashboardPatient, PatientDetail
from app.prediction_service import validate_aki_prediction_result
from scripts.build_local_demo_snapshot import build_snapshot


def test_local_snapshot_is_complete_honest_and_replaceable(tmp_path: Path) -> None:
    assert build_snapshot(tmp_path, patient_count=3) == 3

    dashboard = json.loads((tmp_path / "dashboard-100.json").read_text(encoding="utf-8"))
    rows = [DashboardPatient.model_validate(row) for row in dashboard["rows"]]
    assert dashboard["source"] == "local_deterministic_synthetic_fallback"
    assert len(rows) == 3
    assert all(row.patient.display_name for row in rows)
    assert all(row.prediction.status == "unavailable" for row in rows)
    assert all("local_snapshot_fallback" in row.prediction.warnings for row in rows)

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
        assert prediction.status == "unavailable"
        assert prediction.reasons == ["local_snapshot_no_stored_prediction"]
