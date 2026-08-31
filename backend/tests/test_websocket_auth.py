import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.services.auth_service import AuthenticationError, AuthService, AuthorizationError
from app.websocket.connection_manager import ConnectionManager

CURRENT_USER = CurrentUser(
    id="user-1",
    firebase_uid="firebase-uid-1",
    name="Sarah Chen",
    email="sarah@example.com",
    organization_id="org-1",
    role="member",
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    connection_manager: ConnectionManager,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with TestClient(app) as test_client:
        test_client.app.state.connection_manager = connection_manager
        yield test_client
    app.dependency_overrides.clear()


def test_websocket_rejects_missing_token(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/ws"):
            pass


def test_websocket_rejects_invalid_token(
    client: TestClient,
    mock_auth_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = AuthenticationError("Invalid authentication token")

    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=bad-token"):
            pass

    mock_auth_service.authenticate.assert_called_once_with("bad-token")


def test_websocket_rejects_unregistered_user(
    client: TestClient,
    mock_auth_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = AuthorizationError(
        "User is not registered in the application"
    )

    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=valid-token"):
            pass


def test_websocket_registers_and_unregisters_authenticated_connection(
    client: TestClient,
    mock_auth_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = CURRENT_USER

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text("ping")
        error_response = json.loads(websocket.receive_text())
        assert error_response["type"] == "error"
        assert len(connection_manager._connections) == 1
        metadata = next(iter(connection_manager._connections.values())).metadata
        assert metadata.user_id == "user-1"
        assert metadata.organization_id == "org-1"
        assert metadata.user_name == "Sarah Chen"
        websocket.close()

    assert len(connection_manager._connections) == 0
