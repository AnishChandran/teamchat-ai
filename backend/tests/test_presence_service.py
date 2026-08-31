import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.auth import CurrentUser
from app.models.events import PresenceUser
from app.services.presence_service import PresenceService
from app.websocket.connection_manager import ConnectionManager

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

USER_ONE = CurrentUser(
    id="user-1",
    firebase_uid="firebase-1",
    name="Sarah Chen",
    email="sarah@example.com",
    organization_id="org-1",
    role="member",
)

USER_TWO = CurrentUser(
    id="user-2",
    firebase_uid="firebase-2",
    name="Mike Ross",
    email="mike@example.com",
    organization_id="org-1",
    role="member",
)


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


def test_get_room_presence_users_deduplicates_multiple_connections(
    manager: ConnectionManager,
) -> None:
    socket_one = AsyncMock()
    socket_two = AsyncMock()
    first = manager.register(socket_one, USER_ONE)
    second = manager.register(socket_two, USER_ONE)
    manager.join_room(first.connection_id, "org-1", "room-1")
    manager.join_room(second.connection_id, "org-1", "room-1")

    users = manager.get_room_presence_users("org-1", "room-1")

    assert users == [PresenceUser(id="user-1", name="Sarah Chen")]


def test_get_room_presence_users_removes_user_after_last_connection_leaves(
    manager: ConnectionManager,
) -> None:
    socket_one = AsyncMock()
    socket_two = AsyncMock()
    first = manager.register(socket_one, USER_ONE)
    second = manager.register(socket_two, USER_ONE)
    manager.join_room(first.connection_id, "org-1", "room-1")
    manager.join_room(second.connection_id, "org-1", "room-1")

    manager.leave_room(first.connection_id, "org-1", "room-1")
    assert manager.get_room_presence_users("org-1", "room-1") == [
        PresenceUser(id="user-1", name="Sarah Chen")
    ]

    manager.leave_room(second.connection_id, "org-1", "room-1")
    assert manager.get_room_presence_users("org-1", "room-1") == []


def test_unregister_returns_affected_rooms(manager: ConnectionManager) -> None:
    socket = AsyncMock()
    metadata = manager.register(socket, USER_ONE)
    manager.join_room(metadata.connection_id, "org-1", "room-1")
    manager.join_room(metadata.connection_id, "org-1", "room-2")

    affected_rooms = manager.unregister(metadata.connection_id)

    assert set(affected_rooms) == {("org-1", "room-1"), ("org-1", "room-2")}
    assert manager.get_room_presence_users("org-1", "room-1") == []


def test_broadcast_room_presence_sends_snapshot(manager: ConnectionManager) -> None:
    socket = AsyncMock()
    metadata = manager.register(socket, USER_ONE)
    manager.join_room(metadata.connection_id, "org-1", "room-1")
    service = PresenceService(manager)

    asyncio.run(service.broadcast_room_presence("org-1", "room-1"))

    socket.send_text.assert_awaited_once()
    payload = socket.send_text.await_args.args[0]
    assert '"type": "presence_updated"' in payload
    assert '"roomId": "room-1"' in payload
    assert '"id": "user-1"' in payload
    assert '"name": "Sarah Chen"' in payload


def test_presence_is_scoped_by_organization(manager: ConnectionManager) -> None:
    org_b_user = USER_TWO.model_copy(update={"organization_id": "org-2"})
    socket_a = AsyncMock()
    socket_b = AsyncMock()
    conn_a = manager.register(socket_a, USER_ONE)
    conn_b = manager.register(socket_b, org_b_user)
    manager.join_room(conn_a.connection_id, "org-1", "room-1")
    manager.join_room(conn_b.connection_id, "org-2", "room-1")

    org_a_users = manager.get_room_presence_users("org-1", "room-1")
    org_b_users = manager.get_room_presence_users("org-2", "room-1")

    assert org_a_users == [PresenceUser(id="user-1", name="Sarah Chen")]
    assert org_b_users == [PresenceUser(id="user-2", name="Mike Ross")]
