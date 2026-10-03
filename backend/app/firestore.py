from typing import Any

from .firebase import get_firebase_app


def get_firestore_client() -> Any:
    """Return the Admin Firestore client without importing it during app startup."""
    from firebase_admin import firestore

    return firestore.client(app=get_firebase_app())
