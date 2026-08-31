import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.models.auth import CurrentUser
from app.models.events import PresenceUser
from app.services.typing_service import TypingService
from app.websocket.connection_manager import ConnectionManager

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


@pytest.fixture
def service(manager: ConnectionManager) -> TypingService:
    return TypingService(manager, ttl_seconds=0.1)


def test_get_typing_users_returns_empty_when_no_one_is_typing(service: TypingService) -> None:
    assert service.get_typing_users("org-1", "room-1") == []


def test_set_typing_adds_user_to_snapshot(
    manager: ConnectionManager,
    service: TypingService,
) -> None:
    socket = AsyncMock()
    metadata = manager.register(socket, USER_ONE)
    manager.join_room(metadata.connection_id, "org-1", "room-1")

    asyncio.run(
        service.set_typing(
            "org-1",
            "room-1",
            USER_ONE.id,
            USER_ONE.name,
            True,
            metadata.connection_id,
        )
    )

    assert service.get_typing_users("org-1", "room-1") == [
        PresenceUser(id="user-1", name="Sarah Chen")
    ]


def test_set_typing_deduplicates_multiple_connections_for_same_user(
    manager: ConnectionManager,
    service: TypingService,
) -> None:
    socket_one = AsyncMock()
    socket_two = AsyncMock()
    first = manager.register(socket_one, USER_ONE)
    second = manager.register(socket_two, USER_ONE)
    manager.join_room(first.connection_id, "org-1", "room-1")
    manager.join_room(second.connection_id, "org-1", "room-1")

    asyncio.run(
        service.set_typing(
            "org-1",
            "room-1",
            USER_ONE.id,
            USER_ONE.name,
            True,
            first.connection_id,
        )
    )
    asyncio.run(
        service.set_typing(
            "org-1",
            "room-1",
            USER_ONE.id,
            USER_ONE.name,
            True,
            second.connection_id,
        )
    )

    assert service.get_typing_users("org-1", "room-1") == [
        PresenceUser(id="user-1", name="Sarah Chen")
    ]


def test_set_typing_false_removes_user(service: TypingService) -> None:
    asyncio.run(
        service.set_typing("org-1", "room-1", USER_ONE.id, USER_ONE.name, True, "conn-1")
    )
    asyncio.run(
        service.set_typing("org-1", "room-1", USER_ONE.id, USER_ONE.name, False, "conn-1")
    )

    assert service.get_typing_users("org-1", "room-1") == []


def test_typing_expires_after_ttl(service: TypingService) -> None:
    asyncio.run(
        service.set_typing("org-1", "room-1", USER_ONE.id, USER_ONE.name, True, "conn-1")
    )

    asyncio.run(asyncio.sleep(0.15))

    assert service.get_typing_users("org-1", "room-1") == []


def test_broadcast_typing_excludes_sender(
    manager: ConnectionManager,
    service: TypingService,
) -> None:
    sender_socket = AsyncMock()
    observer_socket = AsyncMock()
    sender = manager.register(sender_socket, USER_ONE)
    observer = manager.register(observer_socket, USER_TWO)
    manager.join_room(sender.connection_id, "org-1", "room-1")
    manager.join_room(observer.connection_id, "org-1", "room-1")

    asyncio.run(
        service.set_typing(
            "org-1",
            "room-1",
            USER_ONE.id,
            USER_ONE.name,
            True,
            sender.connection_id,
        )
    )

    sender_socket.send_text.assert_not_awaited()
    observer_socket.send_text.assert_awaited_once()
    payload = observer_socket.send_text.await_args.args[0]
    assert '"type": "typing_updated"' in payload
    assert '"roomId": "room-1"' in payload
    assert '"id": "user-1"' in payload
    assert '"name": "Sarah Chen"' in payload


def test_clear_user_in_room_and_broadcast_removes_user(
    manager: ConnectionManager,
    service: TypingService,
) -> None:
    observer_socket = AsyncMock()
    observer = manager.register(observer_socket, USER_TWO)
    manager.join_room(observer.connection_id, "org-1", "room-1")

    asyncio.run(
        service.set_typing("org-1", "room-1", USER_ONE.id, USER_ONE.name, True, "conn-1")
    )
    observer_socket.send_text.reset_mock()
    asyncio.run(service.clear_user_in_room_and_broadcast("org-1", "room-1", USER_ONE.id))

    assert service.get_typing_users("org-1", "room-1") == []
    observer_socket.send_text.assert_awaited_once()
    payload = json.loads(observer_socket.send_text.await_args.args[0])
    assert payload == {
        "type": "typing_updated",
        "payload": {"roomId": "room-1", "users": []},
    }


def test_typing_is_scoped_by_organization(service: TypingService) -> None:
    asyncio.run(
        service.set_typing("org-1", "room-1", USER_ONE.id, USER_ONE.name, True, "conn-1")
    )
    asyncio.run(
        service.set_typing("org-2", "room-1", USER_TWO.id, USER_TWO.name, True, "conn-2")
    )

    assert service.get_typing_users("org-1", "room-1") == [
        PresenceUser(id="user-1", name="Sarah Chen")
    ]
    assert service.get_typing_users("org-2", "room-1") == [
        PresenceUser(id="user-2", name="Mike Ross")
    ]
