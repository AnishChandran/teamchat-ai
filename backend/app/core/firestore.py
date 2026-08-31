from google.cloud.firestore import Client

from firebase_admin import firestore as admin_firestore

from app.core.firebase import get_firebase_app

_client: Client | None = None


def get_firestore_client() -> Client:
    global _client
    if _client is None:
        app = get_firebase_app()
        _client = admin_firestore.client(app=app)
    return _client


def reset_firestore_client() -> None:
    global _client
    _client = None
