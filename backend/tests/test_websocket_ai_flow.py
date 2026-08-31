import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Message, Room
from app.services.ai_chat_service import AiChatService
from app.services.auth_service import AuthService
from app.services.message_service import MessageService
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

USER_MESSAGE = Message(
    id="message-1",
    sender_id="user-a",
    sender_name="Org A Member",
    type="user",
    content="@Gemini help us choose a cache",
    created_at=CREATED_AT,
    status="complete",
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_room_authorization_service() -> MagicMock:
    service = MagicMock(spec=RoomAuthorizationService)
    service.get_room_for_user.return_value = SAMPLE_ROOM
    return service


@pytest.fixture
def mock_message_service() -> MagicMock:
    return MagicMock(spec=MessageService)


@pytest.fixture
def mock_ai_chat_service() -> MagicMock:
    return MagicMock(spec=AiChatService)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_service: MagicMock,
    mock_ai_chat_service: MagicMock,
    connection_manager: ConnectionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    scheduled: list[asyncio.Task] = []

    def schedule_task(coro):
        task = asyncio.get_running_loop().create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", schedule_task)
    mock_message_service._room_authorization_service = mock_room_authorization_service
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with TestClient(app) as test_client:
        test_client.app.state.connection_manager = connection_manager
        test_client.app.state.room_authorization_service = mock_room_authorization_service
        test_client.app.state.message_service = mock_message_service
        test_client.app.state.ai_chat_service = mock_ai_chat_service
        test_client.app.state._ai_tasks = scheduled
        yield test_client
    app.dependency_overrides.clear()


def _join_room(websocket, room_id: str = "room-1") -> None:
    websocket.send_text(json.dumps({"type": "join_room", "roomId": room_id}))
    websocket.receive_text()
    websocket.receive_text()


async def _drain_ai_tasks(client: TestClient) -> None:
    tasks = getattr(client.app.state, "_ai_tasks", [])
    if tasks:
        await asyncio.gather(*tasks)


def test_send_message_with_ai_mention_schedules_ai_flow(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
    mock_ai_chat_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.return_value = USER_MESSAGE
    mock_ai_chat_service.handle_mention = AsyncMock()

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        _join_room(websocket)
        websocket.send_text(
            json.dumps(
                {
                    "type": "send_message",
                    "roomId": "room-1",
                    "content": "@Gemini help us choose a cache",
                }
            )
        )
        response = json.loads(websocket.receive_text())
        asyncio.run(_drain_ai_tasks(client))

    assert response["type"] == "message_created"
    assert response["message"]["content"] == "@Gemini help us choose a cache"
    mock_ai_chat_service.handle_mention.assert_awaited_once()
    call_kwargs = mock_ai_chat_service.handle_mention.await_args.kwargs
    assert call_kwargs["organization_id"] == "org-a"
    assert call_kwargs["room_id"] == "room-1"
    assert call_kwargs["room_name"] == "General"
    assert call_kwargs["triggering_message"] == USER_MESSAGE


def test_send_message_without_ai_mention_does_not_schedule_ai_flow(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
    mock_ai_chat_service: MagicMock,
) -> None:
    plain_message = USER_MESSAGE.model_copy(update={"content": "Hello team"})
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.return_value = plain_message

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        _join_room(websocket)
        websocket.send_text(
            json.dumps({"type": "send_message", "roomId": "room-1", "content": "Hello team"})
        )
        response = json.loads(websocket.receive_text())
        asyncio.run(_drain_ai_tasks(client))

    assert response["type"] == "message_created"
    mock_ai_chat_service.handle_mention.assert_not_called()


def _receive_until_type(websocket, event_type: str) -> dict:
    while True:
        event = json.loads(websocket.receive_text())
        if event["type"] == event_type:
            return event


def test_ai_flow_broadcasts_to_all_joined_room_members(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
    mock_ai_chat_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.side_effect = [ORG_A_MEMBER, ORG_A_MEMBER]
    mock_message_service.send_user_message.return_value = USER_MESSAGE

    async def fake_handle_mention(*, broadcast, **kwargs) -> None:
        await broadcast(
            {
                "type": "ai_started",
                "payload": {"roomId": "room-1", "messageId": "ai-msg-1"},
            }
        )
        await broadcast(
            {
                "type": "ai_chunk",
                "payload": {"roomId": "room-1", "messageId": "ai-msg-1", "delta": "Try Redis."},
            }
        )
        await broadcast(
            {
                "type": "ai_completed",
                "payload": {"roomId": "room-1", "messageId": "ai-msg-1"},
            }
        )

    mock_ai_chat_service.handle_mention = AsyncMock(side_effect=fake_handle_mention)

    with client.websocket_connect("/ws?token=valid-token") as sender:
        _join_room(sender)
        with client.websocket_connect("/ws?token=valid-token") as observer:
            _join_room(observer)
            sender.send_text(
                json.dumps(
                    {
                        "type": "send_message",
                        "roomId": "room-1",
                        "content": "@Gemini help us choose a cache",
                    }
                )
            )
            assert _receive_until_type(sender, "message_created")["type"] == "message_created"
            asyncio.run(_drain_ai_tasks(client))
            observer_events = []
            while len(observer_events) < 3:
                event = json.loads(observer.receive_text())
                if event["type"] == "message_created":
                    continue
                observer_events.append(event)

    assert [event["type"] for event in observer_events] == [
        "ai_started",
        "ai_chunk",
        "ai_completed",
    ]
    assert observer_events[1]["payload"]["delta"] == "Try Redis."


def test_ai_error_does_not_close_websocket(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_message_service: MagicMock,
    mock_ai_chat_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_message_service.send_user_message.return_value = USER_MESSAGE

    async def fake_handle_mention(*, broadcast, **kwargs) -> None:
        await broadcast(
            {
                "type": "ai_started",
                "payload": {"roomId": "room-1", "messageId": "ai-msg-1"},
            }
        )
        await broadcast(
            {
                "type": "ai_error",
                "payload": {
                    "roomId": "room-1",
                    "messageId": "ai-msg-1",
                    "message": "AI is temporarily unavailable. Please try again.",
                },
            }
        )

    mock_ai_chat_service.handle_mention = AsyncMock(side_effect=fake_handle_mention)

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        _join_room(websocket)
        websocket.send_text(
            json.dumps(
                {
                    "type": "send_message",
                    "roomId": "room-1",
                    "content": "@Gemini help us choose a cache",
                }
            )
        )
        assert _receive_until_type(websocket, "message_created")["type"] == "message_created"
        asyncio.run(_drain_ai_tasks(client))
        assert json.loads(websocket.receive_text())["type"] == "ai_started"
        error = json.loads(websocket.receive_text())
        assert error["type"] == "ai_error"
        websocket.send_text(json.dumps({"type": "typing", "roomId": "room-1", "isTyping": True}))
        typing_update = json.loads(websocket.receive_text())
        assert typing_update["type"] == "typing_updated"
