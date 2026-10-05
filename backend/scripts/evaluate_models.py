"""Reproducible synthetic held-out comparison for TwinBean research models."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from app.aki_features import FEATURE_SCHEMA, build_training_rows
from app.synthetic_data import generate_cohort
from scripts.train_aki_model import _cohort_checksum, _contexts

EHR_COLUMNS = ("age_years", "latest_creatinine_mg_dl", "creatinine_delta_48h_mg_dl")
COMBINED_COLUMNS = FEATURE_SCHEMA.columns


def _pipeline(columns: tuple[str, ...], seed: int) -> Pipeline:
    features = ColumnTransformer([("numeric", SimpleImputer(strategy="median", add_indicator=True), list(columns))], remainder="drop").set_output(transform="pandas")
    model = XGBClassifier(objective="binary:logistic", eval_metric="logloss", tree_method="hist", n_estimators=120, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=seed, n_jobs=1)
    return Pipeline([("features", features), ("classifier", model)])


def _metrics(labels: list[int], probabilities: list[float]) -> dict[str, float]:
    predictions = [int(value >= 0.5) for value in probabilities]
    return {
        "roc_auc": round(float(roc_auc_score(labels, probabilities)), 6),
        "average_precision": round(float(average_precision_score(labels, probabilities)), 6),
        "brier_score": round(float(brier_score_loss(labels, probabilities)), 6),
        "log_loss": round(float(log_loss(labels, probabilities)), 6),
        "accuracy_at_0_5": round(float(accuracy_score(labels, predictions)), 6),
    }


def evaluate(*, seed: int, patient_count: int, time_basis: datetime) -> dict[str, object]:
    cohort = generate_cohort(seed, "twinbean-synthetic-v1", time_basis, patient_count)
    cutoff = time_basis - timedelta(hours=24)
    rows = build_training_rows(_contexts(cohort), [cutoff] * patient_count)
    labels = list(rows.labels)
    by_class = {0: [], 1: []}
    for index, label in enumerate(labels):
        by_class[label].append(index)
    held_out = sorted(by_class[0][::4] + by_class[1][::4])
    train = [index for index in range(patient_count) if index not in held_out]
    train_groups = {rows.patient_groups[index] for index in train}
    held_groups = {rows.patient_groups[index] for index in held_out}
    if train_groups & held_groups or {labels[index] for index in train} != {0, 1} or {labels[index] for index in held_out} != {0, 1}:
        raise ValueError("patient-level split must be disjoint and contain both classes")
    held_labels = [labels[index] for index in held_out]
    results: dict[str, object] = {}
    for name, columns in (("ehr_only", EHR_COLUMNS), ("combined_ehr_iot", COMBINED_COLUMNS)):
        model = _pipeline(columns, seed)
        model.fit(rows.features.iloc[train][list(columns)], [labels[index] for index in train])
        probabilities = model.predict_proba(rows.features.iloc[held_out][list(columns)])[:, 1].tolist()
        results[name] = {"features": list(columns), "metrics": _metrics(held_labels, probabilities)}
    return {
        "report_version": "twinbean-synthetic-evaluation-v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "synthetic_data_only": True,
        "clinical_validation": False,
        "dataset": {"generator": "TwinBean deterministic synthetic generator (not Synthea)", "seed": seed, "patient_count": patient_count, "cohort_sha256": _cohort_checksum(cohort), "prediction_cutoff": cutoff.isoformat().replace("+00:00", "Z"), "positive_labels": sum(labels), "negative_labels": patient_count - sum(labels)},
        "split": {"strategy": "deterministic stratified patient-level holdout", "train_patients": len(train), "held_out_patients": len(held_out), "patient_overlap": 0, "same_held_out_patients_for_both_models": True},
        "leakage_checks": {"features_filtered_at_or_before_cutoff": True, "labels_use_open_next_24h_window": True, "patient_ids_excluded_from_features": True},
        "models": results,
        "limitations": ["Synthetic data evaluation is not clinical validation.", "The deterministic generator has simplified trajectories and does not represent real prevalence or care processes.", "The 0.5 accuracy threshold is descriptive only and is not a clinical decision threshold."],
    }


def write_report(result: dict[str, object], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    models = result["models"]
    lines = ["# TwinBean Synthetic Model Evaluation", "", "> Research prototype using synthetic data only. These results are not clinical validation.", "", "## Design", "", f"- Dataset: {result['dataset']['patient_count']} deterministic synthetic adult CKD patients; generator is not Synthea.", f"- Split: {result['split']['train_patients']} training and {result['split']['held_out_patients']} held-out patients; overlap 0.", "- Both models use the same held-out patients and the same time-safe cutoff.", "- EHR-only excludes the simulated IoT blood-pressure feature; combined includes it.", "", "## Actual Held-Out Results", "", "| Model | ROC AUC | Average precision | Brier score | Log loss | Accuracy at 0.5 |", "|---|---:|---:|---:|---:|---:|"]
    for name in ("ehr_only", "combined_ehr_iot"):
        metric = models[name]["metrics"]
        lines.append(f"| {name} | {metric['roc_auc']:.3f} | {metric['average_precision']:.3f} | {metric['brier_score']:.3f} | {metric['log_loss']:.3f} | {metric['accuracy_at_0_5']:.3f} |")
    lines += ["", "## Leakage Controls", "", "- Entire patients are held out; no patient appears in both partitions.", "- Feature snapshots include only observations at or before prediction time.", "- Labels use the open next-24-hour window and are never model features.", "- Patient identifiers remain grouping metadata outside the feature matrix.", "", "## Limitations", ""] + [f"- {item}" for item in result["limitations"]]
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--patient-count", type=int, default=80)
    parser.add_argument("--time-basis", default="2026-10-05T00:00:00Z")
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/evals/phase6-model-evaluation.json"))
    parser.add_argument("--report-output", type=Path, default=Path("../docs/MODEL_EVALUATION.md"))
    args = parser.parse_args()
    basis = datetime.fromisoformat(args.time_basis.replace("Z", "+00:00")).astimezone(UTC)
    result = evaluate(seed=args.seed, patient_count=args.patient_count, time_basis=basis)
    write_report(result, args.json_output, args.report_output)
    print(json.dumps({"json": str(args.json_output), "report": str(args.report_output), "held_out_patients": result["split"]["held_out_patients"]}))


if __name__ == "__main__":
    main()
