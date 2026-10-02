from fastapi.testclient import TestClient
import pytest

from app import auth as auth_module
from app.main import app

client = TestClient(app)


def test_doctor_claim_can_reach_protected_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    response = client.get(
        "/health/authenticated",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["authorization"] == "doctor"


def test_non_doctor_claim_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "research-user", "role": "researcher"},
    )

    response = client.get(
        "/health/authenticated",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Doctor access is required."


def test_invalid_token_is_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(_token: str) -> dict[str, str]:
        raise ValueError("invalid")

    monkeypatch.setattr(auth_module, "verify_firebase_token", reject)

    response = client.get(
        "/health/authenticated",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
