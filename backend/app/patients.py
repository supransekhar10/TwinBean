from typing import Any

from pydantic import BaseModel

from .firestore import get_firestore_client


class PatientSummary(BaseModel):
    """Root patient data safe to return from the bounded list endpoint."""

    patient_id: str
    display_name: str
    age: int
    ckd_stage: str


class PatientRepository:
    """Server-only Firestore reads for patient root documents."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_firestore(cls) -> "PatientRepository":
        return cls(get_firestore_client())

    def list_patients(self, limit: int) -> list[PatientSummary]:
        bounded_limit = min(max(limit, 1), 100)
        snapshots = (
            self._client.collection("patients")
            .order_by("patient_id")
            .limit(bounded_limit)
            .stream()
        )
        return [self._summary_from_snapshot(snapshot) for snapshot in snapshots]

    @staticmethod
    def _summary_from_snapshot(snapshot: Any) -> PatientSummary:
        data = snapshot.to_dict() or {}
        return PatientSummary(
            patient_id=str(data["patient_id"]),
            display_name=str(data["display_name"]),
            age=int(data["age"]),
            ckd_stage=str(data["ckd_stage"]),
        )
