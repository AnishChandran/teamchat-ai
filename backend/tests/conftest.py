from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.me import get_organization_repository
from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Organization
from app.services.auth_service import AuthenticationError, AuthorizationError, AuthService

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

SAMPLE_CURRENT_USER = CurrentUser(
    id="user-1",
    firebase_uid="firebase-uid-1",
    name="Sarah Chen",
    email="sarah@example.com",
    organization_id="org-1",
    role="admin",
)

SAMPLE_ORGANIZATION = Organization(
    id="org-1",
    name="Acme Corp",
    slug="acme-corp",
    created_at=CREATED_AT,
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_organization_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_organization_repository: MagicMock,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_organization_repository] = lambda: mock_organization_repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
