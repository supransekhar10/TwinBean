"""Reproducible AKI model release and verified inference helpers.

Joblib is intentionally reached only after a controlled release directory and
every manifest, package, schema, and member checksum have been verified.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version as package_version
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import json
import platform

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from .aki_features import FEATURE_SCHEMA, FRESHNESS_POLICY, LABEL_VERSION


MODEL_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "model_artifacts"
MODEL_VERSION = "aki-24h-2026.10.04"
FEATURE_UNITS = MappingProxyType(
    {
        "age_years": "years",
        "latest_creatinine_mg_dl": "mg/dL",
        "creatinine_delta_48h_mg_dl": "mg/dL",
        "latest_systolic_bp_mmhg": "mmHg",
    }
)
PACKAGE_NAMES = ("pandas", "scikit-learn", "xgboost", "shap")


class ArtifactIntegrityError(RuntimeError):
    """A release is not safe to deserialize or use for an available forecast."""


@dataclass(frozen=True)
class VerifiedBundle:
    pipeline: Pipeline
    manifest: Mapping[str, Any]
    feature_schema: Mapping[str, Any]
    release_dir: Path


def make_aki_pipeline() -> Pipeline:
    """Return the locked combined-stream preprocessing and XGBoost estimator."""

    features = ColumnTransformer(
        [("numeric", SimpleImputer(strategy="median", add_indicator=True), list(FEATURE_SCHEMA.columns))],
        remainder="drop",
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
    classifier = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=20261004,
        n_jobs=1,
    )
    return Pipeline([("features", features), ("classifier", classifier)])


def package_versions() -> dict[str, str]:
    """Return the exact packages whose persistence compatibility is verified."""

    return {name: package_version(name) for name in PACKAGE_NAMES}


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


def release_schema() -> dict[str, Any]:
    return {
        "schema_version": FEATURE_SCHEMA.version,
        "raw_feature_columns": list(FEATURE_SCHEMA.columns),
        "units": dict(FEATURE_UNITS),
    }


def runtime_metadata() -> dict[str, Any]:
    return {"python_version": platform.python_version(), "package_versions": package_versions()}


def load_verified_bundle(controlled_dir: Path, *, artifact_root: Path = MODEL_ARTIFACT_ROOT) -> VerifiedBundle:
    """Verify a configured controlled release fully before deserializing it.

    ``controlled_dir`` is server configuration, never a caller/request value.
    The strict direct-child check prevents path traversal and arbitrary files.
    """

    try:
        root = artifact_root.resolve(strict=True)
        release_dir = controlled_dir.resolve(strict=True)
    except OSError as error:
        raise ArtifactIntegrityError("controlled release directory is unavailable") from error
    if release_dir.parent != root or not release_dir.is_dir():
        raise ArtifactIntegrityError("release directory is outside the controlled artifact store")

    manifest_path = release_dir / "manifest.json"
    schema_path = release_dir / "feature-schema.json"
    pipeline_path = release_dir / "pipeline.joblib"
    manifest = _read_json(manifest_path, "manifest")
    schema = _read_json(schema_path, "feature schema")
    _verify_manifest(manifest, schema, release_dir, pipeline_path, schema_path)

    # No executable-code-adjacent deserialization occurs before this point.
    try:
        pipeline = joblib.load(pipeline_path)
    except Exception as error:  # joblib errors must not become a usable score.
        raise ArtifactIntegrityError("verified pipeline could not be deserialized") from error
    _verify_loaded_pipeline(pipeline, manifest)
    return VerifiedBundle(
        pipeline=pipeline,
        manifest=MappingProxyType(dict(manifest)),
        feature_schema=MappingProxyType(dict(schema)),
        release_dir=release_dir,
    )


def predict_probability(bundle: VerifiedBundle, frame: pd.DataFrame) -> float:
    """Return only a finite positive-class probability for an exact raw frame."""

    if not isinstance(bundle, VerifiedBundle):
        raise ArtifactIntegrityError("inference requires a verified bundle")
    if not isinstance(frame, pd.DataFrame) or len(frame) != 1:
        raise ArtifactIntegrityError("inference requires exactly one feature row")
    if tuple(frame.columns) != FEATURE_SCHEMA.columns:
        raise ArtifactIntegrityError("request frame does not match the verified feature order")
    try:
        probability = float(bundle.pipeline.predict_proba(frame)[0, 1])
    except Exception as error:
        raise ArtifactIntegrityError("verified pipeline could not score the feature row") from error
    if not isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ArtifactIntegrityError("pipeline produced an invalid positive-class probability")
    return probability


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError(f"{label} is missing or invalid") from error
    if not isinstance(value, dict):
        raise ArtifactIntegrityError(f"{label} must be a JSON object")
    return value


def _verify_manifest(
    manifest: Mapping[str, Any], schema: Mapping[str, Any], release_dir: Path, pipeline_path: Path, schema_path: Path
) -> None:
    required = {
        "format_version", "model_version", "synthetic_research_use", "clinical_validated", "code_revision",
        "python_version", "package_versions", "feature_schema", "freshness_policy", "label_version",
        "explanation", "cohort", "partition", "members",
    }
    if not required <= set(manifest):
        raise ArtifactIntegrityError("manifest is incomplete")
    if manifest["format_version"] != 1 or manifest["model_version"] != release_dir.name:
        raise ArtifactIntegrityError("manifest release identity is invalid")
    if manifest["synthetic_research_use"] is not True or manifest["clinical_validated"] is not False:
        raise ArtifactIntegrityError("manifest research-use declaration is invalid")
    if not isinstance(manifest["code_revision"], str) or not manifest["code_revision"]:
        raise ArtifactIntegrityError("manifest code revision is invalid")
    if manifest["python_version"] != platform.python_version() or manifest["package_versions"] != package_versions():
        raise ArtifactIntegrityError("artifact runtime packages are incompatible")
    expected_schema = release_schema()
    if schema != expected_schema or manifest["feature_schema"] != expected_schema:
        raise ArtifactIntegrityError("artifact feature schema is incompatible")
    if manifest["freshness_policy"] != {"version": FRESHNESS_POLICY.version, "maximum_age_hours": 24}:
        raise ArtifactIntegrityError("artifact freshness policy is incompatible")
    if manifest["label_version"] != LABEL_VERSION:
        raise ArtifactIntegrityError("artifact label definition is incompatible")
    if manifest["explanation"] != {"model_output": "raw", "additivity_abs_tol": 1e-6, "semantics": "model_influence_not_causal"}:
        raise ArtifactIntegrityError("artifact explanation contract is incompatible")
    _verify_cohort_metadata(manifest["cohort"])
    _verify_partition_metadata(manifest["partition"])
    transformed_columns = manifest.get("transformed_feature_columns")
    if not isinstance(transformed_columns, list) or not transformed_columns or not all(
        isinstance(column, str) and column for column in transformed_columns
    ):
        raise ArtifactIntegrityError("artifact transformed feature metadata is invalid")
    members = manifest["members"]
    if not isinstance(members, Mapping) or set(members) != {"pipeline.joblib", "feature-schema.json"}:
        raise ArtifactIntegrityError("artifact member manifest is incomplete")
    for expected_path, filename in ((pipeline_path, "pipeline.joblib"), (schema_path, "feature-schema.json")):
        expected_digest = members.get(filename)
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise ArtifactIntegrityError("artifact member digest is invalid")
        try:
            actual_digest = sha256_file(expected_path)
        except OSError as error:
            raise ArtifactIntegrityError("artifact member is unavailable") from error
        if actual_digest != expected_digest:
            raise ArtifactIntegrityError("artifact member checksum mismatch")


def _verify_cohort_metadata(cohort: object) -> None:
    if not isinstance(cohort, Mapping) or set(cohort) != {
        "generator_version", "seed", "time_basis", "patient_count", "snapshot_sha256"
    }:
        raise ArtifactIntegrityError("artifact cohort metadata is incomplete")
    if not isinstance(cohort["generator_version"], str) or not cohort["generator_version"]:
        raise ArtifactIntegrityError("artifact cohort generator metadata is invalid")
    if not isinstance(cohort["seed"], int) or isinstance(cohort["seed"], bool):
        raise ArtifactIntegrityError("artifact cohort seed is invalid")
    if not isinstance(cohort["patient_count"], int) or cohort["patient_count"] < 4:
        raise ArtifactIntegrityError("artifact cohort size is invalid")
    if not isinstance(cohort["time_basis"], str) or not cohort["time_basis"].endswith("Z"):
        raise ArtifactIntegrityError("artifact cohort time basis is invalid")
    if not _is_sha256(cohort["snapshot_sha256"]):
        raise ArtifactIntegrityError("artifact cohort snapshot checksum is invalid")


def _verify_partition_metadata(partition: object) -> None:
    if not isinstance(partition, Mapping) or set(partition) != {
        "development_group_digest", "train_group_digest", "held_out_group_digest", "held_out_patient_count"
    }:
        raise ArtifactIntegrityError("artifact partition metadata is incomplete")
    if not all(_is_sha256(partition[name]) for name in (
        "development_group_digest", "train_group_digest", "held_out_group_digest"
    )):
        raise ArtifactIntegrityError("artifact partition metadata must contain digests only")
    if not isinstance(partition["held_out_patient_count"], int) or partition["held_out_patient_count"] < 1:
        raise ArtifactIntegrityError("artifact held-out partition metadata is invalid")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _verify_loaded_pipeline(pipeline: object, manifest: Mapping[str, Any]) -> None:
    if not isinstance(pipeline, Pipeline) or set(pipeline.named_steps) != {"features", "classifier"}:
        raise ArtifactIntegrityError("deserialized artifact is not the required pipeline")
    features = pipeline.named_steps["features"]
    classifier = pipeline.named_steps["classifier"]
    if not isinstance(features, ColumnTransformer) or not isinstance(classifier, XGBClassifier):
        raise ArtifactIntegrityError("deserialized pipeline components are incompatible")
    try:
        transformed_names = list(features.get_feature_names_out())
        booster_names = classifier.get_booster().feature_names or []
    except Exception as error:
        raise ArtifactIntegrityError("deserialized pipeline is not fitted") from error
    if transformed_names != list(manifest["transformed_feature_columns"]) or booster_names != transformed_names:
        raise ArtifactIntegrityError("deserialized pipeline feature alignment is incompatible")
