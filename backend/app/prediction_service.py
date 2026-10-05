"""Orchestration for separate current-rule and future-AKI prediction results."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .clinical_rules import ClinicalRuleResult, calculate_creatinine_rule
from .patients import ClinicalContext, PatientRepository
from .settings import Settings, get_settings


NON_CAUSAL_SEMANTICS = "model influence in raw-margin/log-odds space; not causal"

class ShapAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str = Field(min_length=1)
    value: float
    expected_value: float
    semantics: Literal["model influence in raw-margin/log-odds space; not causal"] = NON_CAUSAL_SEMANTICS
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


def validate_aki_prediction_result(value: object) -> AkiPredictionResult:
    """Validate a persisted prediction without allowing rule fields into its union."""

    return _PREDICTION_ADAPTER.validate_python(value)


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
        try:
            # Heavy native ML libraries are loaded only for an explicit inference
            # request. Stored-patient reads and authentication must remain usable
            # on hosts where application-control policy blocks those DLLs.
            from .aki_explanations import ExplanationIntegrityError, explain_prediction
            from .aki_features import FEATURE_SCHEMA, FRESHNESS_POLICY, build_prediction_snapshot
            from .aki_model import ArtifactIntegrityError, load_verified_bundle, predict_probability

            snapshot = build_prediction_snapshot(context, prediction_cutoff)
            if snapshot.status != "available" or snapshot.frame is None:
                return self._unavailable(prediction_cutoff, snapshot.reason or "invalid_prediction_input")
            bundle = load_verified_bundle(self._artifact_dir)
            probability = predict_probability(bundle, snapshot.frame)
        except (ImportError, OSError):
            return self._unavailable(prediction_cutoff, "model_engine_unavailable")
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
                    expected_value=item.expected_value,
                    semantics=item.semantics,
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
        prediction = validate_aki_prediction_result(self._engine.predict(context, cutoff))
        envelope = ClinicalResultEnvelope(clinical_rule=clinical_rule, prediction=prediction)
        existing = self._repository.get_existing_clinical_results(context, envelope)
        if existing is not None:
            return ClinicalResultEnvelope.model_validate(existing)
        try:
            self._repository.write_clinical_results(context, envelope)
        except Exception:
            concurrent_winner = self._repository.get_existing_clinical_results(context, envelope)
            if concurrent_winner is not None:
                return ClinicalResultEnvelope.model_validate(concurrent_winner)
            raise
        return envelope


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("prediction_cutoff must be timezone-aware UTC")
    return value.astimezone(UTC)
