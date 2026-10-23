"""Explicit reproducible command for releasing the local synthetic AKI model."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from typing import Sequence
import os
import shutil
import subprocess

import joblib

from app.aki_features import build_training_rows
from app.aki_model import (
    MODEL_ARTIFACT_ROOT,
    MODEL_VERSION,
    canonical_json,
    make_aki_pipeline,
    release_schema,
    runtime_metadata,
    sha256_file,
)
from app.patients import ClinicalContext, PatientDetail, PatientSummary
from app.synthetic_data import MAX_PATIENT_COUNT, SyntheticCohort, generate_cohort


def _utc_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("time must be an ISO-8601 UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise argparse.ArgumentTypeError("time must be UTC")
    return parsed.astimezone(UTC)


def _positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("patient count must be an integer") from error
    if not 4 <= count <= MAX_PATIENT_COUNT:
        raise argparse.ArgumentTypeError(f"patient count must be between 4 and {MAX_PATIENT_COUNT}")
    return count


def _digest(values: Sequence[str]) -> str:
    return sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _cohort_checksum(cohort: SyntheticCohort) -> str:
    from json import dumps

    return sha256(dumps(cohort.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _code_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _contexts(cohort: SyntheticCohort) -> list[ClinicalContext]:
    events: dict[str, list] = defaultdict(list)
    observations: dict[str, list] = defaultdict(list)
    for event in cohort.ehr_events:
        events[event.patient_id].append(event)
    for observation in cohort.iot_observations:
        observations[observation.patient_id].append(observation)
    checksum = _cohort_checksum(cohort)
    return [
        ClinicalContext(
            cohort_id=f"cohort-{checksum[:24]}",
            manifest_checksum=checksum,
            generator_version=cohort.provenance.generator_version,
            seed=cohort.provenance.seed,
            patient=PatientDetail(
                patient=PatientSummary(
                    patient_id=patient.patient_id, display_name=patient.display_name, age=patient.age, ckd_stage=patient.ckd_stage
                ),
                ehr_history=events[patient.patient_id],
                iot_observations=observations[patient.patient_id],
            ),
        )
        for patient in cohort.patients
    ]


def train_release(
    output_dir: Path,
    *,
    artifact_root: Path = MODEL_ARTIFACT_ROOT,
    seed: int,
    generator_version: str,
    time_basis: datetime,
    patient_count: int,
    model_version: str = MODEL_VERSION,
) -> Path:
    """Train only on patient-disjoint development groups and atomically publish one release."""

    root = artifact_root.resolve()
    release = output_dir.resolve()
    if release.parent != root or release.name != model_version:
        raise ValueError("output directory must be the configured controlled model-version directory")
    if release.exists():
        raise ValueError("refusing to replace an existing immutable model release")
    root.mkdir(parents=True, exist_ok=True)
    cohort = generate_cohort(seed, generator_version, time_basis, patient_count)
    cutoff = time_basis - timedelta(hours=24)
    rows = build_training_rows(_contexts(cohort), [cutoff] * patient_count)
    ordered_indices = sorted(range(patient_count), key=lambda index: rows.patient_groups[index])
    train_count = max(2, (patient_count * 3) // 4)
    train_indices, held_out_indices = ordered_indices[:train_count], ordered_indices[train_count:]
    if not held_out_indices or set(rows.patient_groups[index] for index in train_indices) & set(rows.patient_groups[index] for index in held_out_indices):
        raise ValueError("development split must be patient-disjoint")
    labels = [rows.labels[index] for index in train_indices]
    if set(labels) != {0, 1}:
        raise ValueError("development training partition must include both synthetic label classes")
    pipeline = make_aki_pipeline().fit(rows.features.iloc[train_indices], labels)
    transformed_names = list(pipeline.named_steps["features"].get_feature_names_out())

    temp = Path(mkdtemp(prefix=".release-", dir=root))
    try:
        pipeline_path = temp / "pipeline.joblib"
        schema_path = temp / "feature-schema.json"
        joblib.dump(pipeline, pipeline_path)
        schema_path.write_text(canonical_json(release_schema()), encoding="utf-8")
        manifest = {
            "format_version": 1,
            "model_version": model_version,
            "synthetic_research_use": True,
            "clinical_validated": False,
            "code_revision": _code_revision(),
            **runtime_metadata(),
            "feature_schema": release_schema(),
            "freshness_policy": {"version": "required-observation-24h-2026.10.04", "maximum_age_hours": 24},
            "label_version": "new-aki-24h-2026.10.04",
            "explanation": {"model_output": "raw", "additivity_abs_tol": 3e-6, "semantics": "model_influence_not_causal"},
            "cohort": {
                "generator_version": generator_version,
                "seed": seed,
                "time_basis": time_basis.isoformat().replace("+00:00", "Z"),
                "patient_count": patient_count,
                "snapshot_sha256": _cohort_checksum(cohort),
            },
            "partition": {
                "development_group_digest": _digest(rows.patient_groups),
                "train_group_digest": _digest([rows.patient_groups[index] for index in train_indices]),
                "held_out_group_digest": _digest([rows.patient_groups[index] for index in held_out_indices]),
                "held_out_patient_count": len(held_out_indices),
            },
            "transformed_feature_columns": transformed_names,
            "members": {"pipeline.joblib": sha256_file(pipeline_path), "feature-schema.json": sha256_file(schema_path)},
        }
        (temp / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
        temp.replace(release)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return release


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and release TwinBean's synthetic 24-hour AKI research model.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--generator-version", required=True)
    parser.add_argument("--time-basis", type=_utc_time, required=True)
    parser.add_argument("--patient-count", type=_positive_count, required=True)
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--output-dir", type=Path, default=MODEL_ARTIFACT_ROOT / MODEL_VERSION)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    release = train_release(
        args.output_dir,
        seed=args.seed,
        generator_version=args.generator_version,
        time_basis=args.time_basis,
        patient_count=args.patient_count,
        model_version=args.model_version,
    )
    print(f"Released synthetic research AKI bundle at {release}")


if __name__ == "__main__":
    main()
