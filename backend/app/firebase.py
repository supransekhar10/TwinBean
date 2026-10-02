import firebase_admin
from firebase_admin import credentials

from .settings import get_settings


def get_firebase_app() -> firebase_admin.App:
    """Return the process-wide Admin SDK app using backend credentials only."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        options = (
            {"projectId": settings.firebase_project_id}
            if settings.firebase_project_id
            else None
        )
        return firebase_admin.initialize_app(credentials.ApplicationDefault(), options)
