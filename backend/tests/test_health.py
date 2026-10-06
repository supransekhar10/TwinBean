from fastapi.testclient import TestClient
import subprocess
import sys

from app.main import app

client = TestClient(app)


def test_public_health_is_available() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"service": "twinbean-api", "status": "ok"}


def test_authenticated_health_requires_token() -> None:
    response = client.get("/health/authenticated")

    assert response.status_code == 401


def test_cors_preflight_allows_review_note_post_from_frontend() -> None:
    response = client.options(
        "/patients/tbp-11117e11ec4f5392b8b003c66adebd17/review-notes",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


def test_application_startup_does_not_import_native_ml_stack() -> None:
    command = (
        "import sys; import app.main; "
        "blocked = {'pandas', 'shap', 'xgboost'} & set(sys.modules); "
        "print(f'unexpected eager imports: {sorted(blocked)}', file=sys.stderr) if blocked else None; "
        "sys.exit(1 if blocked else 0)"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
