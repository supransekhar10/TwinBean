"""Build an honest local-only synthetic snapshot for an unavailable Firestore demo.

This command never claims that generated records came from Firestore. A later
successful dashboard refresh atomically replaces the dashboard snapshot and
invalidates these patient-level cache files.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.clinical_rules import calculate_creatinine_rule
from app.patients import (
    DashboardClinicalRuleSummary,
    DashboardPatient,
    PatientDetail,
    PatientSummary,
    UnavailableDashboardPrediction,
)
from app.prediction_service import UnavailableAkiPrediction
from app.synthetic_data import generate_cohort


DEFAULT_TIME_BASIS = datetime(2026, 1, 1, tzinfo=UTC)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def build_snapshot(
    cache_dir: Path,
    *,
    seed: int = 2402,
    generator_version: str = "phase2-v1",
    time_basis: datetime = DEFAULT_TIME_BASIS,
    patient_count: int = 12,
) -> int:
    cohort = generate_cohort(seed, generator_version, time_basis, patient_count)
    dashboard_rows: list[DashboardPatient] = []

    for patient in cohort.patients:
        summary = PatientSummary(
            patient_id=patient.patient_id,
            display_name=patient.display_name,
            age=patient.age,
            sex=patient.sex,
            ckd_stage=patient.ckd_stage,
            ckd_context=patient.ckd_context,
        )
        history = sorted(
            (event for event in cohort.ehr_events if event.patient_id == patient.patient_id),
            key=lambda event: (event.event_time, event.event_id),
        )
        observations = sorted(
            (item for item in cohort.iot_observations if item.patient_id == patient.patient_id),
            key=lambda item: (item.observed_at, item.observation_id),
        )
        detail = PatientDetail(patient=summary, ehr_history=history, iot_observations=observations)
        rule = calculate_creatinine_rule(history, time_basis)
        prediction = UnavailableAkiPrediction(
            status="unavailable",
            outcome="new_aki_within_24h",
            prediction_cutoff=time_basis,
            generated_at=time_basis,
            model_version=None,
            reasons=["local_snapshot_no_stored_prediction"],
            warnings=["local_snapshot_fallback"],
        )
        dashboard_rows.append(
            DashboardPatient(
                patient=summary,
                current_rule=DashboardClinicalRuleSummary(
                    status=rule.status,
                    calculation_time=rule.calculation_time,
                    prediction_cutoff=rule.prediction_cutoff,
                    insufficiency_reasons=rule.insufficiency_reasons,
                ),
                prediction=UnavailableDashboardPrediction(
                    status="unavailable",
                    prediction_cutoff=time_basis,
                    generated_at=time_basis,
                    reasons=prediction.reasons,
                    warnings=prediction.warnings,
                ),
            )
        )
        prefix = cache_dir / f"patient-{patient.patient_id}"
        _write_json(
            prefix.with_name(f"{prefix.name}-detail-100.json"),
            {
                "patient": summary.model_dump(mode="json"),
                "ehr_history": [event.to_dict() for event in history],
                "iot_observations": [item.to_dict() for item in observations],
            },
        )
        _write_json(prefix.with_name(f"{prefix.name}-rules-1.json"), [rule.model_dump(mode="json")])
        _write_json(prefix.with_name(f"{prefix.name}-predictions-1.json"), [prediction.model_dump(mode="json")])

    dashboard_rows.sort(key=lambda row: (row.patient.display_name.casefold(), row.patient.patient_id))
    _write_json(
        cache_dir / "dashboard-100.json",
        {
            "synced_at": time_basis.isoformat().replace("+00:00", "Z"),
            "source": "local_deterministic_synthetic_fallback",
            "rows": [row.model_dump(mode="json") for row in dashboard_rows],
        },
    )
    return len(dashboard_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TwinBean's local synthetic demo snapshot.")
    parser.add_argument("--cache-dir", type=Path, default=Path(__file__).resolve().parents[1] / ".cache")
    args = parser.parse_args()
    count = build_snapshot(args.cache_dir)
    print(f"Built local synthetic fallback snapshot for {count} patients.")


if __name__ == "__main__":
    main()
