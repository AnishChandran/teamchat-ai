import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.auth import CurrentUser
from app.services.message_service import MessageService
from app.websocket.connection_manager import ConnectionManager
from app.websocket.event_handler import WebSocketRoomEventHandler

CURRENT_USER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Org A Member",
    email="a@example.com",
    organization_id="org-a",
    role="member",
)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def mock_message_service() -> MagicMock:
    return MagicMock(spec=MessageService)


@pytest.fixture
def event_handler_setup(
    connection_manager: ConnectionManager,
    mock_message_service: MagicMock,
) -> tuple[WebSocketRoomEventHandler, str]:
    websocket = AsyncMock()
    metadata = connection_manager.register(websocket, CURRENT_USER)
    connection_manager.join_room(metadata.connection_id, "org-a", "room-1")
    handler = WebSocketRoomEventHandler(
        connection_id=metadata.connection_id,
        current_user=CURRENT_USER,
        connection_manager=connection_manager,
        message_service=mock_message_service,
    )
    return handler, metadata.connection_id


def test_send_message_firestore_failure_returns_error_event(
    event_handler_setup: tuple[WebSocketRoomEventHandler, str],
    connection_manager: ConnectionManager,
    mock_message_service: MagicMock,
) -> None:
    event_handler, connection_id = event_handler_setup
    mock_message_service.send_user_message.side_effect = RuntimeError("firestore unavailable")

    asyncio.run(
        event_handler.handle_message(
            '{"type":"send_message","roomId":"room-1","content":"Hello"}',
        ),
    )

    connection = connection_manager.get_connection(connection_id)
    assert connection is not None
    sent_payload = connection.websocket.send_text.await_args.args[0]
    assert '"type": "error"' in sent_payload
    assert "Unable to save message" in sent_payload


def test_invalid_payload_returns_error_without_crashing(
    event_handler_setup: tuple[WebSocketRoomEventHandler, str],
    connection_manager: ConnectionManager,
) -> None:
    event_handler, connection_id = event_handler_setup
    asyncio.run(event_handler.handle_message("{not-json"))

    connection = connection_manager.get_connection(connection_id)
    assert connection is not None
    sent_payload = connection.websocket.send_text.await_args.args[0]
    assert "Invalid event payload" in sent_payload
