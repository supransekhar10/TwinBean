"""Explicit command for seeding the deterministic TwinBean synthetic cohort."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from typing import Sequence

from app.patients import PatientRepository
from app.synthetic_data import MAX_PATIENT_COUNT, generate_cohort


def _non_negative_seed(value: str) -> int:
    try:
        seed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("seed must be a non-negative integer") from error
    if seed < 0:
        raise argparse.ArgumentTypeError("seed must be a non-negative integer")
    return seed


def _generator_version(value: str) -> str:
    version = value.strip()
    if not version:
        raise argparse.ArgumentTypeError("generator-version must be non-empty")
    return version


def _utc_time_basis(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("time-basis must be an ISO-8601 UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise argparse.ArgumentTypeError("time-basis must be an ISO-8601 UTC timestamp")
    return parsed.astimezone(UTC)


def _patient_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("patient-count must be a positive integer") from error
    if not 1 <= count <= MAX_PATIENT_COUNT:
        raise argparse.ArgumentTypeError(
            f"patient-count must be between 1 and {MAX_PATIENT_COUNT}"
        )
    return count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed TwinBean's deterministic synthetic CKD cohort into Firestore."
    )
    parser.add_argument("--seed", required=True, type=_non_negative_seed)
    parser.add_argument("--generator-version", required=True, type=_generator_version)
    parser.add_argument("--time-basis", required=True, type=_utc_time_basis)
    parser.add_argument("--patient-count", required=True, type=_patient_count)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Generate and seed a cohort only when this explicit command is invoked."""
    args = _parser().parse_args(argv)
    cohort = generate_cohort(
        seed=args.seed,
        generator_version=args.generator_version,
        time_basis=args.time_basis,
        patient_count=args.patient_count,
    )
    result = PatientRepository.from_firestore().write_cohort(cohort)
    print(
        "Seeded synthetic cohort "
        f"patients={result.patient_count} "
        f"ehr_events={result.ehr_event_count} "
        f"iot_observations={result.iot_observation_count} "
        f"version={args.generator_version} "
        f"seed={args.seed} "
        f"manifest_checksum={result.manifest_checksum}"
    )


if __name__ == "__main__":
    main()
