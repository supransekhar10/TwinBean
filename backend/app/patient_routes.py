from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from .auth import require_doctor
from .patients import PatientRepository, PatientSummary


router = APIRouter()


def get_patient_repository() -> PatientRepository:
    """Provide the server-only repository after doctor authorization succeeds."""
    return PatientRepository.from_firestore()


@router.get("/patients", response_model=list[PatientSummary])
def list_patients(
    _claims: Annotated[dict[str, Any], Depends(require_doctor)],
    repository: Annotated[PatientRepository, Depends(get_patient_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PatientSummary]:
    return repository.list_patients(limit)
