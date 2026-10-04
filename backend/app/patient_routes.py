from datetime import UTC, datetime
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, field_validator

from .auth import require_doctor
from .clinical_rules import ClinicalRuleResult
from .patients import PatientDetail, PatientRepository, PatientSummary
from .prediction_service import AkiPredictionResult, ClinicalResultEnvelope, PredictionService
from .settings import get_settings


router = APIRouter()
_PATIENT_ID_PATTERN = r"^tbp-[0-9a-f]{32}$"
_INFERENCE_LIMITER = anyio.CapacityLimiter(get_settings().aki_inference_concurrency)


def get_patient_repository() -> PatientRepository:
    """Provide the server-only repository after doctor authorization succeeds."""
    return PatientRepository.from_firestore()


def get_prediction_service() -> PredictionService:
    """Construct the server-only clinical orchestration service after authorization."""
    return PredictionService(PatientRepository.from_firestore())


class ClinicalResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_cutoff: datetime

    @field_validator("prediction_cutoff")
    @classmethod
    def timezone_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
            raise ValueError("prediction_cutoff must be timezone-aware UTC")
        return value.astimezone(UTC)


@router.get("/patients", response_model=list[PatientSummary])
def list_patients(
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PatientSummary]:
    return repository.list_patients(limit)


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
) -> PatientDetail:
    detail = repository.get_patient(patient_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return detail


@router.post("/patients/{patient_id}/clinical-results", response_model=ClinicalResultEnvelope)
async def generate_clinical_results(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    request: ClinicalResultRequest,
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> ClinicalResultEnvelope:
    result = await anyio.to_thread.run_sync(
        service.generate,
        patient_id,
        request.prediction_cutoff,
        limiter=_INFERENCE_LIMITER,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return result


@router.get("/patients/{patient_id}/clinical-rules", response_model=list[ClinicalRuleResult])
def list_clinical_rules(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ClinicalRuleResult]:
    return repository.list_clinical_rules(patient_id, limit)


@router.get("/patients/{patient_id}/aki-predictions", response_model=list[AkiPredictionResult])
def list_aki_predictions(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AkiPredictionResult]:
    return repository.list_aki_predictions(patient_id, limit)
