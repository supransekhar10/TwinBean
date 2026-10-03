import sys

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.main import app


client = TestClient(app)


def test_doctor_can_list_typed_root_patient_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    response = client.get(
        "/patients",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "patient_id": "synthetic-001",
            "display_name": "Synthetic Patient 001",
            "age": 64,
            "ckd_stage": "G3b",
        }
    ]
    assert "firebase_admin.firestore" not in sys.modules
