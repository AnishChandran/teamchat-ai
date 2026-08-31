import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Message, Room
from app.repositories.room_repository import RoomNotFoundError
from app.services.auth_service import AuthService
from app.services.message_service import MessageService, MessageValidationError
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

SAMPLE_MESSAGE = Message(
    id="message-1",
    sender_id="user-a",
    sender_name="Org A Member",
    type="user",
    content="Hello team",
    created_at=CREATED_AT,
    status="complete",
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_room_authorization_service() -> MagicMock:
    return MagicMock(spec=RoomAuthorizationService)


@pytest.fixture
def mock_message_service() -> MagicMock:
    return MagicMock(spec=MessageService)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_service: MagicMock,
    connection_manager: ConnectionManager,
) -> TestClient:
    mock_message_service._room_authorization_service = mock_room_authorization_service
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with TestClient(app) as test_client:
        test_client.app.state.connection_manager = connection_manager
        test_client.app.state.room_authorization_service = mock_room_authorization_service
        test_client.app.state.message_service = mock_message_service
        yield test_client
    app.dependency_overrides.clear()


def _join_room(websocket, room_id: str = "room-1") -> None:
    websocket.send_text(json.dumps({"type": "join_room", "roomId": room_id}))
    websocket.receive_text()
    websocket.receive_text()


def test_send_message_broadcasts_to_joined_room_members(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.return_value = SAMPLE_MESSAGE

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        _join_room(websocket)
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-1", "content": "Hello team"})
        )
        response = json.loads(websocket.receive_text())

    assert response["type"] == "message_created"
    assert response["message"]["id"] == "message-1"
    assert response["message"]["senderName"] == "Org A Member"
    assert response["message"]["content"] == "Hello team"
    mock_message_service.send_user_message.assert_called_once_with(
        ORG_A_MEMBER,
        "room-1",
        "Hello team",
    )


def test_send_message_rejects_empty_content(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.side_effect = MessageValidationError(
        "Message content cannot be empty"
    )

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-1", "content": "   "})
        )
        response = json.loads(websocket.receive_text())

    assert response == {
        "type": "error",
        "message": "Message content cannot be empty",
        "roomId": "room-1",
    }


def test_send_message_rejects_non_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.side_effect = RoomAccessDeniedError(
        "Room membership is required for this action"
    )

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-1", "content": "Hello"})
        )
        response = json.loads(websocket.receive_text())

    assert response == {
        "type": "error",
        "message": "Room membership is required for this action",
        "roomId": "room-1",
    }


def test_send_message_rejects_cross_organization_room(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.side_effect = RoomNotFoundError(
        "Room 'room-b1' was not found"
    )

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-b1", "content": "Hello"})
        )
        response = json.loads(websocket.receive_text())

    assert response == {
        "type": "error",
        "message": "Room not found",
        "roomId": "room-b1",
    }


def test_send_message_does_not_broadcast_to_unjoined_connections(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
    connection_manager: ConnectionManager,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.return_value = SAMPLE_MESSAGE

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-1", "content": "Hello team"})
        )
        assert connection_manager.get_room_connection_ids("org-a", "room-1") == set()

    mock_message_service.send_user_message.assert_called_once()
