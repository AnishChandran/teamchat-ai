from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import ServiceUnavailableError
from app.models.domain import User
from app.services.auth_service import AuthenticationError, AuthService, AuthorizationError

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def organization_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_service(user_repository: MagicMock, organization_repository: MagicMock) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        organization_repository=organization_repository,
    )


def test_verify_id_token_returns_decoded_token(auth_service: AuthService) -> None:
    decoded = {"sub": "firebase-uid-1", "organizationId": "org-1"}
    with (
        patch("app.services.auth_service.get_firebase_project_id", return_value="test-project"),
        patch(
            "app.services.auth_service.google_id_token.verify_firebase_token",
            return_value=decoded,
        ),
    ):
        assert auth_service.verify_id_token("token") == {
            "sub": "firebase-uid-1",
            "organizationId": "org-1",
            "uid": "firebase-uid-1",
        }


def test_verify_id_token_raises_authentication_error_on_invalid_token(auth_service: AuthService) -> None:
    with (
        patch("app.services.auth_service.get_firebase_project_id", return_value="test-project"),
        patch(
            "app.services.auth_service.google_id_token.verify_firebase_token",
            side_effect=ValueError("invalid"),
        ),
    ):
        with pytest.raises(AuthenticationError):
            auth_service.verify_id_token("bad-token")


def test_verify_id_token_raises_authentication_error_when_project_unconfigured(
    auth_service: AuthService,
) -> None:
    with patch("app.services.auth_service.get_firebase_project_id", return_value=""):
        with pytest.raises(AuthenticationError, match="not configured"):
            auth_service.verify_id_token("token")


def test_resolve_current_user_returns_current_user(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    user = User(
        id="user-1",
        firebase_uid="firebase-uid-1",
        name="Sarah Chen",
        email="sarah@example.com",
        role="admin",
        created_at=CREATED_AT,
    )
    user_repository.get_user_by_firebase_uid.return_value = user

    current_user = auth_service.resolve_current_user(
        {"uid": "firebase-uid-1", "organizationId": "org-1"}
    )

    assert current_user.id == "user-1"
    assert current_user.firebase_uid == "firebase-uid-1"
    assert current_user.organization_id == "org-1"
    assert current_user.role == "admin"
    user_repository.get_user_by_firebase_uid.assert_called_once_with("org-1", "firebase-uid-1")


def test_resolve_current_user_raises_authorization_error_when_org_claim_missing(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    with pytest.raises(AuthorizationError):
        auth_service.resolve_current_user({"uid": "firebase-uid-1"})

    user_repository.get_user_by_firebase_uid.assert_not_called()


def test_resolve_current_user_raises_service_unavailable_when_repository_fails(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_firebase_uid.side_effect = RuntimeError("firestore down")

    with pytest.raises(ServiceUnavailableError):
        auth_service.resolve_current_user(
            {"uid": "firebase-uid-1", "organizationId": "org-1"}
        )


def test_resolve_current_user_raises_authorization_error_when_user_missing(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_firebase_uid.return_value = None

    with pytest.raises(AuthorizationError):
        auth_service.resolve_current_user(
            {"uid": "firebase-uid-1", "organizationId": "org-1"}
        )
