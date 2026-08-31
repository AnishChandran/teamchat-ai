import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Room
from app.repositories.room_repository import RoomNotFoundError
from app.services.auth_service import AuthService
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService
from app.websocket.connection_manager import ConnectionManager

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ORG_A_MEMBER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Org A Member",
    email="a@example.com",
    organization_id="org-a",
    role="member",
)

SAMPLE_ROOM = Room(
    id="room-1",
    name="General",
    description="Team chat",
    member_ids=["user-a"],
    created_by="user-a",
    created_at=CREATED_AT,
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_room_authorization_service() -> MagicMock:
    return MagicMock(spec=RoomAuthorizationService)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with TestClient(app) as test_client:
        test_client.app.state.connection_manager = connection_manager
        test_client.app.state.room_authorization_service = mock_room_authorization_service
        yield test_client
    app.dependency_overrides.clear()


def test_join_room_allows_authorized_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        response = json.loads(websocket.receive_text())

        assert response == {"type": "room_joined", "roomId": "room-1"}
        assert connection_manager.get_room_connection_ids("org-a", "room-1") != set()
        mock_room_authorization_service.get_room_for_user.assert_called_once_with(
            ORG_A_MEMBER,
            "room-1",
        )


def test_join_room_denies_cross_tenant_access(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.side_effect = RoomNotFoundError(
        "Room 'room-b1' was not found"
    )

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-b1"}))
        response = json.loads(websocket.receive_text())

        assert response == {
            "type": "error",
            "message": "Room not found",
            "roomId": "room-b1",
        }
        assert connection_manager.get_room_connection_ids("org-a", "room-b1") == set()


def test_join_room_denies_non_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.side_effect = RoomAccessDeniedError(
        "Room membership is required for this action"
    )

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        response = json.loads(websocket.receive_text())

        assert response == {
            "type": "error",
            "message": "Room membership is required for this action",
            "roomId": "room-1",
        }
        assert connection_manager.get_room_connection_ids("org-a", "room-1") == set()


def test_leave_room_removes_connection_from_room(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        assert json.loads(websocket.receive_text()) == {"type": "room_joined", "roomId": "room-1"}
        assert json.loads(websocket.receive_text())["type"] == "presence_updated"

        websocket.send_text(json.dumps({"type": "leave_room", "roomId": "room-1"}))
        assert json.loads(websocket.receive_text()) == {"type": "room_left", "roomId": "room-1"}
        assert connection_manager.get_room_connection_ids("org-a", "room-1") == set()
