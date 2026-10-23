"""Build an honest local-only synthetic snapshot for an unavailable Firestore demo.

This command never claims that generated records came from Firestore. A later
successful dashboard refresh replaces the snapshot only after Firestore returns
stored rule and prediction evidence for the cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.clinical_rules import calculate_creatinine_rule
from app.patients import (
    DashboardClinicalRuleSummary,
    DashboardPatient,
    AvailableDashboardPrediction,
    ClinicalContext,
    PatientDetail,
    PatientSummary,
    UnavailableDashboardPrediction,
)
from app.prediction_service import PredictionEngine, VerifiedPredictionEngine
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
    generator_version: str = "phase2-v3",
    time_basis: datetime = DEFAULT_TIME_BASIS,
    patient_count: int = 18,
    prediction_engine: PredictionEngine | None = None,
) -> int:
    cohort = generate_cohort(seed, generator_version, time_basis, patient_count)
    engine = prediction_engine or VerifiedPredictionEngine()
    prediction_cutoff = time_basis - timedelta(hours=24)
    manifest_checksum = hashlib.sha256(
        f"{generator_version}:{seed}:{time_basis.isoformat()}:{patient_count}".encode("utf-8")
    ).hexdigest()
    cohort_id = f"cohort-{manifest_checksum[:24]}"
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
        cutoff_detail = PatientDetail(
            patient=summary,
            ehr_history=[event for event in history if event.event_time <= prediction_cutoff],
            iot_observations=[item for item in observations if item.observed_at <= prediction_cutoff],
        )
        context = ClinicalContext(
            cohort_id=cohort_id,
            manifest_checksum=manifest_checksum,
            generator_version=generator_version,
            seed=seed,
            patient=cutoff_detail,
        )
        rule = calculate_creatinine_rule(cutoff_detail.ehr_history, prediction_cutoff)
        prediction = engine.predict(context, prediction_cutoff)
        if prediction.status == "available":
            dashboard_prediction = AvailableDashboardPrediction(
                status="available",
                probability=prediction.probability,
                prediction_cutoff=prediction.prediction_cutoff,
                generated_at=prediction.generated_at,
                warnings=prediction.warnings,
            )
        else:
            dashboard_prediction = UnavailableDashboardPrediction(
                status="unavailable",
                prediction_cutoff=prediction.prediction_cutoff,
                generated_at=prediction.generated_at,
                reasons=prediction.reasons,
                warnings=prediction.warnings,
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
                prediction=dashboard_prediction,
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

    dashboard_rows.sort(
        key=lambda row: (
            0 if row.prediction.status == "available" else 1,
            -row.prediction.probability if row.prediction.status == "available" else 0.0,
            row.patient.display_name.casefold(),
            row.patient.patient_id,
        )
    )
    _write_json(
        cache_dir / "dashboard-100.json",
        {
            "synced_at": time_basis.isoformat().replace("+00:00", "Z"),
            "source": "local_deterministic_synthetic_model_snapshot",
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
