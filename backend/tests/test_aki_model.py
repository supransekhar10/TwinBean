from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from app import aki_model
from app.aki_features import FEATURE_SCHEMA


def test_pipeline_uses_the_reviewed_schema_and_pinned_xgboost_contract() -> None:
    assert hasattr(aki_model, "make_aki_pipeline")

    pipeline = aki_model.make_aki_pipeline()

    features = pipeline.named_steps["features"]
    classifier = pipeline.named_steps["classifier"]
    assert list(features.transformers[0][2]) == list(FEATURE_SCHEMA.columns)
    assert features.remainder == "drop"
    assert classifier.get_params()["objective"] == "binary:logistic"
    assert classifier.get_params()["eval_metric"] == "logloss"
    assert classifier.get_params()["tree_method"] == "hist"
    assert classifier.get_params()["n_estimators"] == 300
    assert classifier.get_params()["max_depth"] == 3
    assert classifier.get_params()["learning_rate"] == 0.05
    assert classifier.get_params()["subsample"] == 0.8
    assert classifier.get_params()["colsample_bytree"] == 0.8
    assert classifier.get_params()["random_state"] == 20261004
    assert classifier.get_params()["n_jobs"] == 1


@pytest.fixture(scope="module")
def release_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from scripts.train_aki_model import train_release

    artifact_root = tmp_path_factory.mktemp("controlled-artifacts")
    return train_release(
        artifact_root / "aki-24h-2026.10.04",
        artifact_root=artifact_root,
        seed=20261004,
        generator_version="aki-release-generator-2026.10.04",
        time_basis=datetime(2026, 10, 4, 0, 0, tzinfo=UTC),
        patient_count=12,
    )


def test_seeded_release_is_complete_and_metadata_is_stable(release_dir: Path, tmp_path: Path) -> None:
    from scripts.train_aki_model import train_release

    second = train_release(
        tmp_path / "second" / "aki-24h-2026.10.04",
        artifact_root=tmp_path / "second",
        seed=20261004,
        generator_version="aki-release-generator-2026.10.04",
        time_basis=datetime(2026, 10, 4, 0, 0, tzinfo=UTC),
        patient_count=12,
    )

    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    duplicate = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["members"]) == {"pipeline.joblib", "feature-schema.json"}
    assert manifest["partition"]["train_group_digest"] != manifest["partition"]["development_group_digest"]
    assert manifest["partition"]["held_out_patient_count"] > 0
    assert manifest["synthetic_research_use"] is True
    assert manifest["clinical_validated"] is False
    assert manifest == duplicate


def test_loader_rejects_untrusted_or_tampered_members_before_deserialization(release_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.aki_model import ArtifactIntegrityError, load_verified_bundle

    loaded = False

    def forbidden_load(_: object) -> object:
        nonlocal loaded
        loaded = True
        raise AssertionError("joblib.load must not run for rejected bundles")

    monkeypatch.setattr(aki_model.joblib, "load", forbidden_load)
    with pytest.raises(ArtifactIntegrityError):
        load_verified_bundle(tmp_path / "request-selected", artifact_root=release_dir.parent)
    assert loaded is False

    schema = release_dir / "feature-schema.json"
    schema.write_text(schema.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        load_verified_bundle(release_dir, artifact_root=release_dir.parent)
    assert loaded is False


def test_verified_bundle_returns_a_finite_deterministic_positive_probability(release_dir: Path) -> None:
    from app.aki_model import load_verified_bundle, predict_probability

    bundle = load_verified_bundle(release_dir, artifact_root=release_dir.parent)
    frame = pd.DataFrame(
        [[61.0, 1.4, 0.1, 130.0]], columns=list(FEATURE_SCHEMA.columns)
    )

    first = predict_probability(bundle, frame)
    second = predict_probability(bundle, frame)

    assert 0.0 <= first <= 1.0
    assert first == pytest.approx(second, abs=1e-12)
