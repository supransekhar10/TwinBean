from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.clinical_rules import CLINICAL_RULE_VERSION, KDIGO_SOURCE, calculate_creatinine_rule
from app.synthetic_data import EhrEvent


CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
REFERENCE_PATH = Path(__file__).parent / "fixtures" / "aki_reference_scenarios.json"


def _reference_scenarios() -> tuple[dict[str, object], list[dict[str, object]]]:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return reference, reference["scenarios"]


def _event(payload: dict[str, object]) -> EhrEvent:
    event_time = CUTOFF - timedelta(hours=float(payload["hours_before_cutoff"]))
    if payload.get("timestamp_kind") == "naive":
        event_time = event_time.replace(tzinfo=None)
    return EhrEvent(
        event_id=str(payload["id"]),
        patient_id="tbp-reference-patient",
        event_type="laboratory",
        event_time=event_time,
        data={"test_name": "creatinine", "value": payload["value"], "unit": payload["unit"]},
        synthetic=True,
        generator_version="reference-scenarios-v1",
        seed=31415,
        source="twinbean-synthetic-ehr",
    )


@pytest.mark.parametrize("scenario", _reference_scenarios()[1], ids=lambda item: str(item["name"]))
def test_reference_scenarios_match_independently_authored_expected_outcomes(
    scenario: dict[str, object],
) -> None:
    result = calculate_creatinine_rule([_event(event) for event in scenario["events"]], CUTOFF)

    assert result.status == scenario["expected_status"]
    assert result.criteria_evaluated == scenario["expected_criteria_evaluated"]
    assert result.criteria_met == scenario["expected_criteria_met"]
    assert [evidence.event_id for evidence in result.evidence] == scenario["expected_evidence_event_ids"]


def test_rule_result_preserves_supported_scope_and_audit_trail() -> None:
    reference, scenarios = _reference_scenarios()
    threshold = next(item for item in scenarios if item["name"] == "absolute_rise_threshold_at_48_hours")

    result = calculate_creatinine_rule([_event(event) for event in threshold["events"]], CUTOFF)

    assert result.calculation_time == CUTOFF
    assert result.prediction_cutoff == CUTOFF
    assert result.baseline_method == "lowest_creatinine_in_prior_7_days"
    assert result.baseline_value_mg_dl == 1.0
    assert result.baseline_evidence is not None
    assert result.baseline_evidence.event_id == "abs-edge-baseline"
    assert result.source == reference["source"] == KDIGO_SOURCE
    assert result.rule_version == CLINICAL_RULE_VERSION
    assert result.scope == "creatinine-only"
    assert "Urine-output criteria were not assessed" in result.limitation
    assert "no AKI" not in result.limitation.lower()
