import firebase_admin
from firebase_admin import credentials

from app.core.config import get_firebase_project_id

_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    global _app
    if _app is not None:
        return _app

    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    project_id = get_firebase_project_id()
    options = {"projectId": project_id} if project_id else None
    cred = credentials.ApplicationDefault()
    _app = firebase_admin.initialize_app(cred, options)
    return _app


def reset_firebase_app() -> None:
    global _app
    _app = None
