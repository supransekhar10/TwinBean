"""Versioned, creatinine-only current AKI rule calculation for synthetic records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Iterable, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .synthetic_data import EhrEvent


CLINICAL_RULE_VERSION = "kdigo-creatinine-2012-v1"
KDIGO_SOURCE = "KDIGO Clinical Practice Guideline for Acute Kidney Injury (2012), Recommendation 2.1.1"
ABSOLUTE_RISE_CRITERION = "serum_creatinine_rise_0_3_mg_dl_within_48h"
RATIO_CRITERION = "serum_creatinine_ratio_1_5_within_7d"
CreatinineCriterion = Literal[
    "serum_creatinine_rise_0_3_mg_dl_within_48h",
    "serum_creatinine_ratio_1_5_within_7d",
]


class CreatinineEvidence(BaseModel):
    """A unit-validated serum creatinine measurement used by the current-rule path."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    observed_at: datetime
    value_mg_dl: float = Field(gt=0)


class ClinicalRuleResult(BaseModel):
    """Observed creatinine-rule status; intentionally not a future-risk contract."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["criteria_met", "criteria_not_met", "insufficient_creatinine_history"]
    calculation_time: datetime
    prediction_cutoff: datetime
    evidence: list[CreatinineEvidence]
    criteria_evaluated: list[CreatinineCriterion] = Field(default_factory=list)
    criteria_met: list[CreatinineCriterion] = Field(default_factory=list)
    latest_evidence: CreatinineEvidence | None = None
    absolute_rise_reference: CreatinineEvidence | None = None
    absolute_rise_mg_dl: float | None = None
    baseline_method: Literal["lowest_creatinine_in_prior_7_days", "unavailable"] = "unavailable"
    baseline_value_mg_dl: float | None = None
    baseline_evidence: CreatinineEvidence | None = None
    ratio_to_baseline: float | None = None
    insufficiency_reasons: list[str] = Field(default_factory=list)
    source: str = KDIGO_SOURCE
    rule_version: str = CLINICAL_RULE_VERSION
    scope: Literal["creatinine-only"] = "creatinine-only"
    limitation: str = "Urine-output criteria were not assessed; this is a creatinine-only rule result."


def calculate_creatinine_rule(
    ehr_history: Sequence[EhrEvent], prediction_cutoff: datetime
) -> ClinicalRuleResult:
    """Evaluate supported KDIGO 2012 serum-creatinine criteria at a fixed UTC cutoff.

    Only data available at the cutoff is considered.  A negative result means no
    supported *creatinine* criterion was met; it never represents a full AKI
    assessment because this prototype has no validated urine-output input.
    """
    cutoff = _require_utc(prediction_cutoff)
    evidence, invalid_reasons = _validated_cutoff_evidence(ehr_history, cutoff)
    if invalid_reasons:
        return _insufficient_result(cutoff, evidence, invalid_reasons)
    if not evidence:
        return _insufficient_result(cutoff, [], ["no_valid_creatinine_evidence"])

    latest = evidence[-1]
    absolute_reference = _lowest_evidence(
        item
        for item in evidence
        if latest.observed_at - timedelta(hours=48) <= item.observed_at < latest.observed_at
    )
    baseline = _lowest_evidence(
        item
        for item in evidence
        if latest.observed_at - timedelta(days=7) <= item.observed_at < latest.observed_at
    )

    criteria_evaluated: list[CreatinineCriterion] = []
    criteria_met: list[CreatinineCriterion] = []
    absolute_rise_mg_dl: float | None = None
    ratio_to_baseline: float | None = None
    if absolute_reference is not None:
        criteria_evaluated.append(ABSOLUTE_RISE_CRITERION)
        absolute_rise_mg_dl = round(latest.value_mg_dl - absolute_reference.value_mg_dl, 6)
        if absolute_rise_mg_dl >= 0.3:
            criteria_met.append(ABSOLUTE_RISE_CRITERION)
    if baseline is not None:
        criteria_evaluated.append(RATIO_CRITERION)
        ratio_to_baseline = round(latest.value_mg_dl / baseline.value_mg_dl, 6)
        if ratio_to_baseline >= 1.5:
            criteria_met.append(RATIO_CRITERION)

    selected_evidence = _selected_evidence(latest, absolute_reference, baseline)
    if not criteria_evaluated:
        return _insufficient_result(
            cutoff,
            selected_evidence,
            ["no_reproducible_creatinine_comparison"],
            latest=latest,
        )

    return ClinicalRuleResult(
        status="criteria_met" if criteria_met else "criteria_not_met",
        calculation_time=cutoff,
        prediction_cutoff=cutoff,
        evidence=selected_evidence,
        criteria_evaluated=criteria_evaluated,
        criteria_met=criteria_met,
        latest_evidence=latest,
        absolute_rise_reference=absolute_reference,
        absolute_rise_mg_dl=absolute_rise_mg_dl,
        baseline_method="lowest_creatinine_in_prior_7_days" if baseline else "unavailable",
        baseline_value_mg_dl=baseline.value_mg_dl if baseline else None,
        baseline_evidence=baseline,
        ratio_to_baseline=ratio_to_baseline,
    )


def _validated_cutoff_evidence(
    ehr_history: Sequence[EhrEvent], cutoff: datetime
) -> tuple[list[CreatinineEvidence], list[str]]:
    evidence: list[CreatinineEvidence] = []
    invalid_reasons: list[str] = []
    for event in ehr_history:
        if event.event_type != "laboratory" or event.data.get("test_name") != "creatinine":
            continue
        try:
            observed_at = _require_utc(event.event_time)
        except ValueError:
            invalid_reasons.append("non_utc_creatinine_time")
            continue
        if observed_at > cutoff:
            continue
        value = event.data.get("value")
        if event.data.get("unit") != "mg/dL":
            invalid_reasons.append("unsupported_creatinine_unit")
            continue
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            or value <= 0
        ):
            invalid_reasons.append("invalid_creatinine_value")
            continue
        evidence.append(
            CreatinineEvidence(
                event_id=event.event_id,
                observed_at=observed_at,
                value_mg_dl=float(value),
            )
        )
    evidence.sort(key=lambda item: (item.observed_at, item.event_id))
    return evidence, sorted(set(invalid_reasons))


def _lowest_evidence(items: Iterable[CreatinineEvidence]) -> CreatinineEvidence | None:
    candidates = list(items)
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item.value_mg_dl, item.observed_at, item.event_id))


def _selected_evidence(*items: CreatinineEvidence | None) -> list[CreatinineEvidence]:
    selected = {item.event_id: item for item in items if item is not None}
    return sorted(selected.values(), key=lambda item: (item.observed_at, item.event_id))


def _insufficient_result(
    cutoff: datetime,
    evidence: list[CreatinineEvidence],
    reasons: list[str],
    *,
    latest: CreatinineEvidence | None = None,
) -> ClinicalRuleResult:
    return ClinicalRuleResult(
        status="insufficient_creatinine_history",
        calculation_time=cutoff,
        prediction_cutoff=cutoff,
        evidence=evidence,
        latest_evidence=latest,
        insufficiency_reasons=reasons,
    )


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("prediction cutoff and rule evidence timestamps must be timezone-aware UTC")
    return value.astimezone(UTC)
