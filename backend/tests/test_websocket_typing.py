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
from app.services.typing_service import TypingService
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

ORG_B_MEMBER = CurrentUser(
    id="user-b",
    firebase_uid="firebase-b",
    name="Org B Member",
    email="b@example.com",
    organization_id="org-a",
    role="member",
)

SAMPLE_ROOM = Room(
    id="room-1",
    name="General",
    description="Team chat",
    member_ids=["user-a", "user-b"],
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
def typing_service(connection_manager: ConnectionManager) -> TypingService:
    return TypingService(connection_manager, ttl_seconds=5.0)


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    connection_manager: ConnectionManager,
    typing_service: TypingService,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with TestClient(app) as test_client:
        test_client.app.state.connection_manager = connection_manager
        test_client.app.state.room_authorization_service = mock_room_authorization_service
        test_client.app.state.typing_service = typing_service
        yield test_client
    app.dependency_overrides.clear()


def join_room(websocket, room_id: str = "room-1") -> None:
    websocket.send_text(json.dumps({"type": "join_room", "roomId": room_id}))
    websocket.receive_text()
    websocket.receive_text()


def test_typing_broadcasts_snapshot_to_other_connections(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = [ORG_A_MEMBER, ORG_B_MEMBER]
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as typer:
        join_room(typer)

        with client.websocket_connect("/ws?token=valid-token") as observer:
            join_room(observer)
            typer.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))
            typing_update = json.loads(observer.receive_text())

    assert typing_update == {
        "type": "typing_updated",
        "payload": {
            "roomId": "room-1",
            "users": [{"id": "user-a", "name": "Org A Member"}],
        },
    }


def test_typing_requires_joined_room(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        websocket.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))
        error = json.loads(websocket.receive_text())

    assert error == {
        "type": "error",
        "message": "Join the room before sending typing updates",
        "roomId": "room-1",
    }


def test_typing_false_clears_user_from_snapshot(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = [ORG_A_MEMBER, ORG_B_MEMBER]
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as typer:
        join_room(typer)

        with client.websocket_connect("/ws?token=valid-token") as observer:
            join_room(observer)
            typer.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))
            observer.receive_text()
            typer.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": False}))
            typing_update = json.loads(observer.receive_text())

    assert typing_update == {
        "type": "typing_updated",
        "payload": {"roomId": "room-1", "users": []},
    }


def test_leave_room_clears_typing_for_user(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = [ORG_A_MEMBER, ORG_B_MEMBER]
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as typer:
        join_room(typer)
        typer.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))

        with client.websocket_connect("/ws?token=valid-token") as observer:
            join_room(observer)
            typer.send_text(json.dumps({"type": "leave_room", "roomId": "room-1"}))
            typer.receive_text()
            typing_update = json.loads(observer.receive_text())
            observer.receive_text()

    assert typing_update == {
        "type": "typing_updated",
        "payload": {"roomId": "room-1", "users": []},
    }


def test_disconnect_clears_typing_for_user(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    typing_service: TypingService,
) -> None:
    mock_auth_service.authenticate.side_effect = [ORG_A_MEMBER, ORG_B_MEMBER]
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM

    with client.websocket_connect("/ws?token=valid-token") as typer:
        join_room(typer)
        typer.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))

        with client.websocket_connect("/ws?token=valid-token") as observer:
            join_room(observer)
            observer.receive_text()
            typer.close()

            typing_update = json.loads(observer.receive_text())
            observer.receive_text()

    assert typing_update == {
        "type": "typing_updated",
        "payload": {"roomId": "room-1", "users": []},
    }
    assert typing_service.get_typing_users("org-a", "room-1") == []
