from typing import Any

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from .firebase import get_firebase_app

bearer_scheme = HTTPBearer(auto_error=False)


def verify_firebase_token(token: str) -> dict[str, Any]:
    return auth.verify_id_token(token, app=get_firebase_app(), check_revoked=True)


def require_doctor(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Firebase ID token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_firebase_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Firebase ID token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access is required.",
        )

    return claims
