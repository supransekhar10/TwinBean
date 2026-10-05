"""Publish bounded TwinBean clinical results and evaluation metadata to Firestore."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from app.firebase import get_firebase_app
from app.firestore import get_firestore_client
from app.patients import PatientRepository
from app.prediction_service import PredictionService


REPORT_PATH = "twinbean_research_reports/phase6-model-evaluation"


def _utc_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(None):
        raise argparse.ArgumentTypeError("prediction cutoff must be UTC")
    return parsed.astimezone(UTC)


def _load_report(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("synthetic_data_only") is not True
        or payload.get("clinical_validation") is not False
    ):
        raise ValueError("evaluation report must be synthetic-only and not clinically validated")
    return payload


def publish(
    *,
    expected_project: str,
    prediction_cutoff: datetime,
    evaluation_report: Path,
    max_patients: int,
) -> dict[str, object]:
    app = get_firebase_app()
    actual_project = str(app.project_id or "")
    if actual_project != expected_project:
        raise ValueError("configured Firebase project does not match the approved target")
    if not 1 <= max_patients <= 100:
        raise ValueError("max patients must be between 1 and 100")

    client = get_firestore_client()
    repository = PatientRepository(client)
    service = PredictionService(repository)
    patients = repository.list_patients(max_patients)
    if not patients:
        raise ValueError("active synthetic cohort is empty")

    available = unavailable = 0
    for patient in patients:
        result = service.generate(patient.patient_id, prediction_cutoff)
        if result is None:
            raise ValueError("active cohort patient disappeared during publication")
        if result.prediction.status == "available":
            available += 1
        else:
            unavailable += 1

    for patient in patients:
        if len(repository.list_clinical_rules(patient.patient_id, 1)) != 1:
            raise ValueError("clinical rule readback failed")
        if len(repository.list_aki_predictions(patient.patient_id, 1)) != 1:
            raise ValueError("prediction readback failed")

    report = _load_report(evaluation_report)
    client.document(REPORT_PATH).set(
        {
            **report,
            "source": "twinbean-synthetic-evaluation",
            "data_classification": "synthetic",
            "report_path": REPORT_PATH,
        }
    )
    readback = client.document(REPORT_PATH).get().to_dict()
    if readback is None or readback.get("report_version") != report.get("report_version"):
        raise ValueError("evaluation report readback failed")

    return {
        "project": actual_project,
        "patients": len(patients),
        "clinical_rules": len(patients),
        "predictions": len(patients),
        "available_predictions": available,
        "unavailable_predictions": unavailable,
        "evaluation_report": REPORT_PATH,
        "prediction_cutoff": prediction_cutoff.isoformat().replace("+00:00", "Z"),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-project", required=True)
    parser.add_argument("--prediction-cutoff", required=True, type=_utc_time)
    parser.add_argument("--evaluation-report", required=True, type=Path)
    parser.add_argument("--max-patients", type=int, default=100)
    parser.add_argument("--confirm-write", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_write:
        parser.error("--confirm-write is required")
    print(json.dumps(publish(
        expected_project=args.expected_project,
        prediction_cutoff=args.prediction_cutoff,
        evaluation_report=args.evaluation_report,
        max_patients=args.max_patients,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
