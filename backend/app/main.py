from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_doctor
from .settings import get_settings

settings = get_settings()
app = FastAPI(title="TwinBean API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
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
