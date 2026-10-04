from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.main import app


PATIENT_ID = "tbp-0123456789abcdef0123456789abcdef"
CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
client = TestClient(app)


def _request(headers: dict[str, str] | None = None) -> object:
    return client.post(
        f"/patients/{PATIENT_ID}/clinical-results",
        headers=headers,
        json={"prediction_cutoff": CUTOFF.isoformat().replace("+00:00", "Z")},
    )


def test_doctor_can_generate_separate_current_rule_and_unavailable_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "demo-doctor", "role": "doctor"},
    )

    response = _request({"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"clinical_rule", "prediction"}
    assert payload["clinical_rule"]["scope"] == "creatinine-only"
    assert payload["prediction"]["status"] == "unavailable"
    assert payload["prediction"]["reasons"]
    assert "probability" not in payload["prediction"]
    assert "attributions" not in payload["prediction"]


def test_missing_token_never_runs_clinical_work() -> None:
    response = _request()
    assert response.status_code == 401


def test_non_doctor_token_never_runs_clinical_work(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "verify_firebase_token",
        lambda _token: {"uid": "research-user", "role": "researcher"},
    )

    response = _request({"Authorization": "Bearer valid-token"})

    assert response.status_code == 403
