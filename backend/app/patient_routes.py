from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, field_validator

from .auth import require_doctor
from .clinical_rules import ClinicalRuleResult
from .patients import DashboardPatient, PatientDetail, PatientRepository, PatientSummary, ReviewNote
from .patient_report import build_patient_report
from .prediction_service import AkiPredictionResult, ClinicalResultEnvelope, PredictionService
from .settings import get_settings
from .twini import TwiniRequest, TwiniResponse, TwiniService


router = APIRouter()
_PATIENT_ID_PATTERN = r"^tbp-[0-9a-f]{32}$"
_INFERENCE_LIMITER = anyio.CapacityLimiter(get_settings().aki_inference_concurrency)


@lru_cache(maxsize=1)
def get_patient_repository() -> PatientRepository:
    """Provide the server-only repository after doctor authorization succeeds."""
    return PatientRepository.from_firestore()


def get_prediction_service() -> PredictionService:
    """Construct the server-only clinical orchestration service after authorization."""
    return PredictionService(get_patient_repository())


def get_twini_service() -> TwiniService:
    return TwiniService(get_settings(), get_patient_repository())


class ClinicalResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_cutoff: datetime

    @field_validator("prediction_cutoff")
    @classmethod
    def timezone_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
            raise ValueError("prediction_cutoff must be timezone-aware UTC")
        return value.astimezone(UTC)


class ReviewNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not 1 <= len(cleaned) <= 2000:
            raise ValueError("note must contain 1 to 2000 characters")
        return cleaned


@router.post("/assistant/chat", response_model=TwiniResponse)
async def chat_with_twini(
    request: TwiniRequest,
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    service: Annotated[TwiniService, Depends(get_twini_service)],
) -> TwiniResponse:
    try:
        return await anyio.to_thread.run_sync(service.answer, request)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.") from error
    except Exception as error:
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twini is temporarily unavailable. Check the backend Groq configuration and retry.",
        ) from error


@router.get("/patients", response_model=list[PatientSummary], response_model_exclude_none=True)
def list_patients(
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PatientSummary]:
    return repository.list_patients(limit)


@router.get("/dashboard/patients", response_model=list[DashboardPatient])
def list_dashboard_patients(
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    refresh: Annotated[bool, Query()] = False,
) -> list[DashboardPatient]:
    """Return stored dashboard evidence without prediction-generation side effects."""
    return repository.list_dashboard_patients(limit, refresh=refresh)


@router.get("/patients/{patient_id}", response_model=PatientDetail, response_model_exclude_none=True)
def get_patient(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
) -> PatientDetail:
    detail = repository.get_patient(patient_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return detail


@router.get("/patients/{patient_id}/review-notes", response_model=list[ReviewNote])
def list_review_notes(patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)], _claims: Annotated[dict[str, Any], Depends(require_doctor)], repository: Annotated[PatientRepository, Depends(get_patient_repository)], limit: Annotated[int, Query(ge=1, le=50)] = 20) -> list[ReviewNote]:
    return repository.list_review_notes(patient_id, limit)


@router.post("/patients/{patient_id}/review-notes", response_model=ReviewNote, status_code=status.HTTP_201_CREATED)
def create_review_note(patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)], request: ReviewNoteRequest, claims: Annotated[dict[str, Any], Depends(require_doctor)], repository: Annotated[PatientRepository, Depends(get_patient_repository)]) -> ReviewNote:
    note = repository.create_review_note(patient_id, str(claims["uid"]), request.text)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return note


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


@router.get("/patients/{patient_id}/report.pdf")
def download_patient_report(
    patient_id: Annotated[str, Path(pattern=_PATIENT_ID_PATTERN)],
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
) -> Response:
    detail = repository.get_patient(patient_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    rules = repository.list_clinical_rules(patient_id, 1)
    predictions = repository.list_aki_predictions(patient_id, 1)
    notes = repository.list_review_notes(patient_id, 20)
    pdf = build_patient_report(detail, rules[0] if rules else None, predictions[0] if predictions else None, notes)
    safe_name = "-".join(part for part in detail.patient.display_name.lower().split() if part.isalnum()) or "patient"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="twinbean-{safe_name}-report.pdf"', "Cache-Control": "no-store"})
