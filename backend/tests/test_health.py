from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_health_is_available() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"service": "twinbean-api", "status": "ok"}


def test_authenticated_health_requires_token() -> None:
    response = client.get("/health/authenticated")

    assert response.status_code == 401
