from typing import Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted, ServiceUnavailable

from .auth import require_doctor
from .patient_routes import router as patient_router
from .settings import get_settings

settings = get_settings()
app = FastAPI(title="TwinBean API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(patient_router)


@app.exception_handler(ResourceExhausted)
@app.exception_handler(DeadlineExceeded)
@app.exception_handler(ServiceUnavailable)
def firestore_temporarily_unavailable(_request: Request, _error: Exception) -> JSONResponse:
    """Expose a safe, retryable response without leaking datastore details."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": (
                "Patient data is temporarily unavailable because Firestore could not complete the request. "
                "Please retry shortly."
            )
        },
        headers={"Retry-After": "300"},
    )


@app.get("/health/live")
def public_health() -> dict[str, str]:
    return {"service": "twinbean-api", "status": "ok"}


@app.get("/health/authenticated")
def authenticated_health(
    claims: dict[str, Any] = Depends(require_doctor),
) -> dict[str, str]:
    return {
        "service": "twinbean-api",
        "status": "ok",
        "authorization": "doctor",
        "uid": str(claims["uid"]),
    }
