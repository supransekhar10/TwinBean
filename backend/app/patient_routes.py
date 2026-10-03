from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from .auth import require_doctor
from .patients import PatientDetail, PatientRepository, PatientSummary


router = APIRouter()
_PATIENT_ID_PATTERN = r"^tbp-[0-9a-f]{32}$"


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
