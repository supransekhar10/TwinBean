from datetime import UTC, datetime

from scripts.evaluate_models import evaluate


def test_evaluation_is_patient_disjoint_time_safe_and_comparative() -> None:
    result = evaluate(seed=20261005, patient_count=40, time_basis=datetime(2026, 10, 5, tzinfo=UTC))
    assert result["split"]["patient_overlap"] == 0
    assert result["split"]["same_held_out_patients_for_both_models"] is True
    assert result["leakage_checks"] == {"features_filtered_at_or_before_cutoff": True, "labels_use_open_next_24h_window": True, "patient_ids_excluded_from_features": True}
    assert set(result["models"]) == {"ehr_only", "combined_ehr_iot"}
    for model in result["models"].values():
        assert all(0 <= value <= 5 for value in model["metrics"].values())
    assert result["clinical_validation"] is False
