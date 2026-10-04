from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest


REFERENCE_PATH = Path(__file__).parent / "fixtures" / "aki_reference_scenarios.json"


def _reference() -> dict[str, object]:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def test_reference_fixture_has_independent_safety_rubric_distribution() -> None:
    reference = _reference()
    categories = reference["scenario_categories"]
    assert len(categories["rule"]) >= 8
    assert len(categories["valid_forecast"]) >= 6
    assert len(categories["unavailable_or_adversarial"]) >= 8
    assert len(categories["end_to_end_integrity"]) >= 2

    for category in categories.values():
        for scenario in category:
            assert scenario["synthetic_provenance"]["generator_version"]
            assert isinstance(scenario["synthetic_provenance"]["seed"], int)
            assert scenario["expected"]
            assert scenario["source"]
            assert scenario["rubric_version"]
            assert scenario["reviewer_role"]


EVALUATOR_SPEC = importlib.util.find_spec("scripts.evaluate_phase3_contract")


def test_evaluator_module_is_available_for_the_reference_release_gate() -> None:
    assert EVALUATOR_SPEC is not None


@pytest.mark.skipif(EVALUATOR_SPEC is None, reason="evaluator is introduced by this plan")
def test_evaluator_runs_all_critical_scenarios_and_writes_a_non_empty_manifest(tmp_path: Path) -> None:
    evaluator = importlib.import_module("scripts.evaluate_phase3_contract")
    output = tmp_path / "phase3-contract.json"

    manifest = evaluator.evaluate_contract(REFERENCE_PATH, output, fail_on_rubric=True)

    assert output.exists()
    assert manifest["scenario_counts"]["total"] >= 24
    assert manifest["critical_failures"] == []
    assert manifest["rubric_counts"]
    assert manifest["output_digest"]

MANIFEST_VERIFIER_SPEC = importlib.util.find_spec("scripts.verify_eval_manifest")


def test_manifest_verifier_module_is_available() -> None:
    assert MANIFEST_VERIFIER_SPEC is not None


@pytest.mark.skipif(MANIFEST_VERIFIER_SPEC is None, reason="verifier is introduced by this plan")
def test_manifest_verifier_rejects_tampering_and_unmanifested_claims(tmp_path: Path) -> None:
    evaluator = importlib.import_module("scripts.evaluate_phase3_contract")
    verifier = importlib.import_module("scripts.verify_eval_manifest")
    output = tmp_path / "phase3-contract.json"
    evaluator.evaluate_contract(REFERENCE_PATH, output, fail_on_rubric=True)
    assert verifier.verify_manifest(output) is True

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["output_digest"] = "0" * 64
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        verifier.verify_manifest(output)
