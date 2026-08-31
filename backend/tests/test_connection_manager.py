import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.auth import CurrentUser
from app.websocket.connection_manager import ConnectionManager

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

CURRENT_USER = CurrentUser(
    id="user-1",
    firebase_uid="firebase-uid-1",
    name="Sarah Chen",
    email="sarah@example.com",
    organization_id="org-1",
    role="member",
)

OTHER_ORG_USER = CurrentUser(
    id="user-2",
    firebase_uid="firebase-uid-2",
    name="Mike Ross",
    email="mike@example.com",
    organization_id="org-2",
    role="member",
)


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def websocket() -> AsyncMock:
    return AsyncMock()


def test_register_stores_connection_metadata(
    manager: ConnectionManager,
    websocket: AsyncMock,
) -> None:
    metadata = manager.register(websocket, CURRENT_USER)

    assert metadata.user_id == "user-1"
    assert metadata.organization_id == "org-1"
    assert metadata.user_name == "Sarah Chen"
    assert manager.get_connection(metadata.connection_id) is not None


def test_unregister_removes_connection_and_room_memberships(
    manager: ConnectionManager,
    websocket: AsyncMock,
) -> None:
    metadata = manager.register(websocket, CURRENT_USER)
    manager.join_room(metadata.connection_id, "org-1", "room-1")

    manager.unregister(metadata.connection_id)

    assert manager.get_connection(metadata.connection_id) is None
    assert manager.get_room_connection_ids("org-1", "room-1") == set()


def test_send_to_connection_sends_json_payload(
    manager: ConnectionManager,
    websocket: AsyncMock,
) -> None:
    metadata = manager.register(websocket, CURRENT_USER)

    asyncio.run(manager.send_to_connection(metadata.connection_id, {"type": "ping"}))

    websocket.send_text.assert_awaited_once_with('{"type": "ping"}')


def test_send_to_connection_removes_stale_connection(
    manager: ConnectionManager,
    websocket: AsyncMock,
) -> None:
    metadata = manager.register(websocket, CURRENT_USER)
    websocket.send_text.side_effect = RuntimeError("connection closed")

    asyncio.run(manager.send_to_connection(metadata.connection_id, {"type": "ping"}))

    assert manager.get_connection(metadata.connection_id) is None


def test_broadcast_to_room_sends_only_to_room_connections(
    manager: ConnectionManager,
) -> None:
    room_one_socket = AsyncMock()
    room_two_socket = AsyncMock()
    other_org_socket = AsyncMock()

    room_one = manager.register(room_one_socket, CURRENT_USER)
    room_two = manager.register(room_two_socket, CURRENT_USER)
    other_org = manager.register(other_org_socket, OTHER_ORG_USER)

    manager.join_room(room_one.connection_id, "org-1", "room-1")
    manager.join_room(room_two.connection_id, "org-1", "room-2")
    manager.join_room(other_org.connection_id, "org-2", "room-1")

    asyncio.run(manager.broadcast_to_room("org-1", "room-1", {"type": "message_created"}))

    room_one_socket.send_text.assert_awaited_once()
    room_two_socket.send_text.assert_not_awaited()
    other_org_socket.send_text.assert_not_awaited()


def test_leave_room_removes_connection_from_room_set(
    manager: ConnectionManager,
    websocket: AsyncMock,
) -> None:
    metadata = manager.register(websocket, CURRENT_USER)
    manager.join_room(metadata.connection_id, "org-1", "room-1")

    manager.leave_room(metadata.connection_id, "org-1", "room-1")

    assert manager.get_room_connection_ids("org-1", "room-1") == set()
    connection = manager.get_connection(metadata.connection_id)
    assert connection is not None
    assert connection.room_keys == set()
