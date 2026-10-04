"""Orchestration for separate current-rule and future-AKI prediction results."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .aki_explanations import ExplanationIntegrityError, explain_prediction
from .aki_features import FEATURE_SCHEMA, FRESHNESS_POLICY, build_prediction_snapshot
from .aki_model import ArtifactIntegrityError, load_verified_bundle, predict_probability
from .clinical_rules import ClinicalRuleResult, calculate_creatinine_rule
from .patients import ClinicalContext, PatientRepository
from .settings import Settings, get_settings


class ShapAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str = Field(min_length=1)
    value: float
    shap_margin: float


class AvailableAkiPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"]
    outcome: Literal["new_aki_within_24h"]
    probability: float = Field(ge=0.0, le=1.0)
    prediction_cutoff: datetime
    generated_at: datetime
    model_version: str
    feature_schema_version: str
    freshness_policy_version: str
    warnings: list[str] = Field(default_factory=list)
    attributions: list[ShapAttribution]


class UnavailableAkiPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unavailable"]
    outcome: Literal["new_aki_within_24h"]
    prediction_cutoff: datetime
    generated_at: datetime
    model_version: str | None = None
    reasons: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)


AkiPredictionResult = Annotated[
    AvailableAkiPrediction | UnavailableAkiPrediction,
    Field(discriminator="status"),
]
_PREDICTION_ADAPTER = TypeAdapter(AkiPredictionResult)


class ClinicalResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinical_rule: ClinicalRuleResult
    prediction: AkiPredictionResult


class PredictionEngine(Protocol):
    def predict(self, context: ClinicalContext, prediction_cutoff: datetime) -> AkiPredictionResult: ...


class VerifiedPredictionEngine:
    """Fail-closed, server-configured XGBoost and SHAP inference for one context."""

    def __init__(self, settings: Settings | None = None) -> None:
        configured = settings or get_settings()
        self._artifact_dir: Path = configured.aki_model_artifact_dir

    def predict(self, context: ClinicalContext, prediction_cutoff: datetime) -> AkiPredictionResult:
        snapshot = build_prediction_snapshot(context, prediction_cutoff)
        if snapshot.status != "available" or snapshot.frame is None:
            return self._unavailable(prediction_cutoff, snapshot.reason or "invalid_prediction_input")

        try:
            bundle = load_verified_bundle(self._artifact_dir)
            probability = predict_probability(bundle, snapshot.frame)
        except ArtifactIntegrityError:
            return self._unavailable(prediction_cutoff, "model_artifact_or_inference_unavailable")

        try:
            explanation = explain_prediction(bundle, snapshot.frame)
        except ExplanationIntegrityError:
            return self._unavailable(prediction_cutoff, "shap_explanation_unavailable")

        return AvailableAkiPrediction(
            status="available",
            outcome="new_aki_within_24h",
            probability=probability,
            prediction_cutoff=prediction_cutoff,
            generated_at=datetime.now(UTC),
            model_version=str(bundle.manifest["model_version"]),
            feature_schema_version=FEATURE_SCHEMA.version,
            freshness_policy_version=FRESHNESS_POLICY.version,
            warnings=[],
            attributions=[
                ShapAttribution(
                    feature=item.feature,
                    value=item.value,
                    shap_margin=item.shap_margin,
                )
                for item in explanation
            ],
        )

    @staticmethod
    def _unavailable(prediction_cutoff: datetime, reason: str) -> UnavailableAkiPrediction:
        return UnavailableAkiPrediction(
            status="unavailable",
            outcome="new_aki_within_24h",
            prediction_cutoff=prediction_cutoff,
            generated_at=datetime.now(UTC),
            model_version=None,
            reasons=[reason],
            warnings=[],
        )


class SafeUnavailablePredictionEngine:
    """Test-only safe fallback retained for explicit injected failure simulations."""

    def predict(self, context: ClinicalContext, prediction_cutoff: datetime) -> AkiPredictionResult:
        return UnavailableAkiPrediction(
            status="unavailable",
            outcome="new_aki_within_24h",
            prediction_cutoff=prediction_cutoff,
            generated_at=prediction_cutoff,
            model_version=None,
            reasons=["model_engine_unavailable"],
            warnings=["Synthetic research prediction is unavailable until a verified model engine is released."],
        )


class PredictionService:
    def __init__(self, repository: PatientRepository, engine: PredictionEngine | None = None) -> None:
        self._repository = repository
        self._engine = engine or VerifiedPredictionEngine()

    def generate(self, patient_id: str, prediction_cutoff: datetime) -> ClinicalResultEnvelope | None:
        cutoff = _require_utc(prediction_cutoff)
        context = self._repository.get_clinical_context(patient_id)
        if context is None:
            return None
        clinical_rule = calculate_creatinine_rule(context.patient.ehr_history, cutoff)
        prediction = _PREDICTION_ADAPTER.validate_python(
            self._engine.predict(context, cutoff)
        )
        envelope = ClinicalResultEnvelope(clinical_rule=clinical_rule, prediction=prediction)
        self._repository.write_clinical_results(context, envelope)
        return envelope


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("prediction_cutoff must be timezone-aware UTC")
    return value.astimezone(UTC)
