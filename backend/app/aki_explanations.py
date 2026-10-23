"""Fail-closed raw-margin SHAP explanations for a verified AKI model bundle."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite

import numpy as np
import pandas as pd
import shap

from .aki_features import FEATURE_SCHEMA
from .aki_model import ArtifactIntegrityError, VerifiedBundle


# XGBoost emits float32 margins while SHAP aggregates feature contributions in
# float64. A three-micro margin tolerance covers the observed four-feature
# accumulation error without masking a materially inconsistent explanation.
RAW_MARGIN_TOLERANCE = 3e-6
NON_CAUSAL_SEMANTICS = "model influence in raw-margin/log-odds space; not causal"


class ExplanationIntegrityError(RuntimeError):
    """An explanation failed a gate and must invalidate the forecast result."""


@dataclass(frozen=True)
class ShapAttribution:
    feature: str
    value: float
    shap_margin: float
    expected_value: float
    semantics: str = NON_CAUSAL_SEMANTICS


def explain_prediction(bundle: VerifiedBundle, frame: pd.DataFrame) -> tuple[ShapAttribution, ...]:
    """Explain one exact transformed frame or raise a typed fail-closed error.

    SHAP values and the XGBoost output margin are deliberately reconciled in
    raw-margin/log-odds space.  They are model influence, not a clinical cause.
    """

    try:
        if not isinstance(bundle, VerifiedBundle):
            raise ExplanationIntegrityError("explanations require a verified bundle")
        if not isinstance(frame, pd.DataFrame) or len(frame) != 1 or tuple(frame.columns) != FEATURE_SCHEMA.columns:
            raise ExplanationIntegrityError("explanation frame does not match the verified raw feature contract")
        features = bundle.pipeline.named_steps["features"]
        classifier = bundle.pipeline.named_steps["classifier"]
        transformed = features.transform(frame)
        if not isinstance(transformed, pd.DataFrame):
            raise ExplanationIntegrityError("preprocessing did not preserve named transformed columns")
        transformed_names = list(features.get_feature_names_out())
        expected_names = list(bundle.manifest["transformed_feature_columns"])
        booster_names = classifier.get_booster().feature_names or []
        if list(transformed.columns) != transformed_names or transformed_names != expected_names or booster_names != transformed_names:
            raise ExplanationIntegrityError("transformed and booster feature names are not exactly aligned")

        explainer = shap.TreeExplainer(classifier, model_output="raw")
        values = np.asarray(explainer.shap_values(transformed, check_additivity=True), dtype=float)
        if values.shape != (1, len(transformed_names)) or not np.isfinite(values).all():
            raise ExplanationIntegrityError("SHAP values are malformed or non-finite")
        expected_values = np.asarray(explainer.expected_value, dtype=float).reshape(-1)
        if len(expected_values) != 1 or not isfinite(float(expected_values[0])):
            raise ExplanationIntegrityError("SHAP expected value is malformed or non-finite")
        raw_margins = np.asarray(classifier.predict(transformed, output_margin=True), dtype=float).reshape(-1)
        if len(raw_margins) != 1 or not isfinite(float(raw_margins[0])):
            raise ExplanationIntegrityError("classifier raw margin is malformed or non-finite")
        expected_value = float(expected_values[0])
        shap_sum = float(values[0].sum())
        raw_margin = float(raw_margins[0])
        if not isclose(expected_value + shap_sum, raw_margin, rel_tol=0.0, abs_tol=RAW_MARGIN_TOLERANCE):
            raise ExplanationIntegrityError("SHAP values do not reconcile with the classifier raw margin")
        return tuple(
            ShapAttribution(
                feature=name,
                value=float(transformed.iloc[0][name]),
                shap_margin=float(value),
                expected_value=expected_value,
            )
            for name, value in zip(transformed_names, values[0], strict=True)
        )
    except ExplanationIntegrityError:
        raise
    except (ArtifactIntegrityError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise ExplanationIntegrityError("SHAP explanation integrity verification failed") from error
