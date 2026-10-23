from fastapi.testclient import TestClient

from app.auth import require_doctor
from app.main import app
from app.patient_routes import get_twini_service
from app.twini import TwiniCitation, TwiniRequest, TwiniResponse


client = TestClient(app)


class _FakeTwini:
    def answer(self, request: TwiniRequest) -> TwiniResponse:
        assert request.question == "What is TwinBean?"
        return TwiniResponse(
            answer="TwinBean is a synthetic kidney digital twin research prototype [Project brief].",
            citations=[TwiniCitation(source="PROJECT.md", label="Project brief")],
            patient_context_used=False,
        )


def test_twini_requires_doctor_token() -> None:
    response = client.post("/assistant/chat", json={"question": "What is TwinBean?"})
    assert response.status_code == 401


def test_twini_returns_grounded_answer_for_doctor() -> None:
    app.dependency_overrides[require_doctor] = lambda: {"uid": "doctor-1", "role": "doctor"}
    app.dependency_overrides[get_twini_service] = lambda: _FakeTwini()
    try:
        response = client.post("/assistant/chat", json={"question": "What is TwinBean?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_context_used"] is False
    assert payload["citations"] == [{"source": "PROJECT.md", "label": "Project brief"}]
    assert "synthetic kidney digital twin" in payload["answer"]


def test_twini_rejects_unbounded_question() -> None:
    app.dependency_overrides[require_doctor] = lambda: {"uid": "doctor-1", "role": "doctor"}
    app.dependency_overrides[get_twini_service] = lambda: _FakeTwini()
    try:
        response = client.post("/assistant/chat", json={"question": "x" * 2001})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
