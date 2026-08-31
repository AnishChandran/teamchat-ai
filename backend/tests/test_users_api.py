from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.dependencies.services import get_user_repository
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import User
from tests.conftest import auth_header

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ORG_A_USER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Org A Member",
    email="a@example.com",
    organization_id="org-a",
    role="member",
)

ORG_B_USER = CurrentUser(
    id="user-b",
    firebase_uid="firebase-b",
    name="Org B Member",
    email="b@example.com",
    organization_id="org-b",
    role="member",
)

SAMPLE_USERS = [
    User(
        id="user-a",
        firebase_uid="firebase-a",
        name="Org A Member",
        email="a@example.com",
        role="member",
        created_at=CREATED_AT,
    ),
    User(
        id="user-c",
        firebase_uid="firebase-c",
        name="Org A Admin",
        email="admin@example.com",
        role="admin",
        created_at=CREATED_AT,
    ),
]


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_user_repository: MagicMock,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_users_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/users")
    assert response.status_code == 401


def test_list_users_returns_organization_members(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_user_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_USER
    mock_user_repository.list_users_for_organization.return_value = SAMPLE_USERS

    response = client.get("/api/users", headers=auth_header())

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "id": "user-a",
                "name": "Org A Member",
                "email": "a@example.com",
                "role": "member",
            },
            {
                "id": "user-c",
                "name": "Org A Admin",
                "email": "admin@example.com",
                "role": "admin",
            },
        ],
    }
    mock_user_repository.list_users_for_organization.assert_called_once_with("org-a")


def test_list_users_scopes_to_current_user_organization(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_user_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_B_USER
    mock_user_repository.list_users_for_organization.return_value = []

    response = client.get("/api/users", headers=auth_header())

    assert response.status_code == 200
    assert response.json() == {"users": []}
    mock_user_repository.list_users_for_organization.assert_called_once_with("org-b")
