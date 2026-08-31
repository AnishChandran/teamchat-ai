import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Room
from app.services.auth_service import AuthService
from app.services.room_authorization_service import RoomAuthorizationService
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


def test_join_room_broadcasts_presence_snapshot(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        assert json.loads(websocket.receive_text()) == {"type": "room_joined", "roomId": "room-1"}
        presence = json.loads(websocket.receive_text())

    assert presence == {
        "type": "presence_updated",
        "payload": {
            "roomId": "room-1",
            "users": [{"id": "user-a", "name": "Org A Member"}],
        },
    }


def test_multiple_connections_for_same_user_do_not_duplicate_presence(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket_one:
        websocket_one.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        websocket_one.receive_text()
        websocket_one.receive_text()

        with client.websocket_connect("/ws?token=valid-token") as websocket_two:
            websocket_two.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
            websocket_two.receive_text()
            presence = json.loads(websocket_two.receive_text())

            assert presence["payload"]["users"] == [{"id": "user-a", "name": "Org A Member"}]


def test_leave_room_updates_presence_when_last_connection_leaves(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        websocket.receive_text()
        websocket.receive_text()

        websocket.send_text(json.dumps({"type": "leave_room", "roomId": "room-1"}))
        assert json.loads(websocket.receive_text()) == {"type": "room_left", "roomId": "room-1"}
        assert connection_manager.get_room_connection_ids("org-a", "room-1") == set()

    assert connection_manager.get_room_presence_users("org-a", "room-1") == []


def test_disconnect_cleans_up_room_presence(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "join_room", "roomId": "room-1"}))
        websocket.receive_text()
        websocket.receive_text()
        websocket.close()

    assert connection_manager.get_room_presence_users("org-a", "room-1") == []
