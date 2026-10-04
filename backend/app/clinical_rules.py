"""Versioned, creatinine-only current AKI rule calculation for synthetic records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .synthetic_data import EhrEvent


CLINICAL_RULE_VERSION = "kdigo-creatinine-2012-v1"
KDIGO_SOURCE = "KDIGO Clinical Practice Guideline for Acute Kidney Injury (2012)"


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
    source: str = KDIGO_SOURCE
    rule_version: str = CLINICAL_RULE_VERSION
    scope: Literal["creatinine-only"] = "creatinine-only"
    limitation: str = "Urine-output criteria were not assessed; this is a creatinine-only rule result."


def calculate_creatinine_rule(
    ehr_history: Sequence[EhrEvent], prediction_cutoff: datetime
) -> ClinicalRuleResult:
    """Evaluate only supported KDIGO creatinine thresholds at a fixed UTC cutoff.

    The selected seven-day minimum is preserved in ``evidence`` so the result remains
    auditable without implying a complete AKI assessment.
    """
    cutoff = _require_utc(prediction_cutoff)
    evidence = sorted(
        (_creatinine_evidence(event) for event in ehr_history if event.event_time <= cutoff),
        key=lambda item: item.observed_at,
    )
    evidence = [item for item in evidence if item is not None]
    if not evidence:
        return ClinicalRuleResult(
            status="insufficient_creatinine_history",
            calculation_time=cutoff,
            prediction_cutoff=cutoff,
            evidence=[],
        )

    latest = evidence[-1]
    last_48_hours = [item for item in evidence if item.observed_at >= cutoff - timedelta(hours=48)]
    last_7_days = [item for item in evidence if item.observed_at >= cutoff - timedelta(days=7)]
    if not last_7_days:
        return ClinicalRuleResult(
            status="insufficient_creatinine_history",
            calculation_time=cutoff,
            prediction_cutoff=cutoff,
            evidence=evidence,
        )

    baseline = min(last_7_days, key=lambda item: item.value_mg_dl)
    delta_criterion = any(
        latest.value_mg_dl - item.value_mg_dl >= 0.3
        for item in last_48_hours
        if item.observed_at <= latest.observed_at
    )
    ratio_criterion = latest.value_mg_dl >= 1.5 * baseline.value_mg_dl
    return ClinicalRuleResult(
        status="criteria_met" if delta_criterion or ratio_criterion else "criteria_not_met",
        calculation_time=cutoff,
        prediction_cutoff=cutoff,
        evidence=evidence,
    )


def _creatinine_evidence(event: EhrEvent) -> CreatinineEvidence | None:
    if event.event_type != "laboratory" or event.data.get("test_name") != "creatinine":
        return None
    value = event.data.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if event.data.get("unit") != "mg/dL":
        return None
    return CreatinineEvidence(
        event_id=event.event_id,
        observed_at=_require_utc(event.event_time),
        value_mg_dl=float(value),
    )


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("prediction cutoff and rule evidence timestamps must be timezone-aware UTC")
    return value.astimezone(UTC)
