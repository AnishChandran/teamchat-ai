from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest

from app.llm.gemini_service import GeminiRequest, GeminiService
from app.models.domain import Message
from app.services.ai_chat_service import AiChatService
from app.services.message_service import MessageService
from app.services.room_authorization_service import RoomAuthorizationService

CREATED_AT = datetime(2026, 2, 8, 14, 30, tzinfo=timezone.utc)
LATER = datetime(2026, 2, 8, 14, 31, tzinfo=timezone.utc)

SARAH_MESSAGE = Message(
    id="msg-sarah",
    sender_id="user-a",
    sender_name="Sarah",
    type="user",
    content="We should evaluate Redis.",
    created_at=CREATED_AT,
    status="complete",
)

MIKE_MESSAGE = Message(
    id="msg-mike",
    sender_id="user-b",
    sender_name="Mike",
    type="user",
    content="Latency matters for this feature.",
    created_at=LATER,
    status="complete",
)

STREAMING_MESSAGE = Message(
    id="msg-stream",
    sender_id="gemini",
    sender_name="Gemini",
    type="ai",
    content="partial...",
    created_at=LATER,
    status="streaming",
)

TRIGGER_MESSAGE = Message(
    id="msg-trigger",
    sender_id="user-a",
    sender_name="Sarah",
    type="user",
    content="@Gemini what caching strategy should we use?",
    created_at=LATER,
    status="complete",
)


@pytest.fixture
def message_repository() -> MagicMock:
    repository = MagicMock()
    repository.allocate_message_id.return_value = "ai-msg-1"
    repository.get_messages.return_value = [
        SARAH_MESSAGE,
        MIKE_MESSAGE,
        STREAMING_MESSAGE,
        TRIGGER_MESSAGE,
    ]
    repository.create_message_with_id.return_value = Message(
        id="ai-msg-1",
        sender_id="gemini",
        sender_name="Gemini",
        type="ai",
        content="Use Redis.",
        created_at=LATER,
        status="complete",
    )
    return repository


@pytest.fixture
def gemini_service() -> MagicMock:
    return MagicMock(spec=GeminiService)


@pytest.fixture
def ai_chat_service(
    message_repository: MagicMock,
    gemini_service: MagicMock,
) -> AiChatService:
    return AiChatService(
        message_repository=message_repository,
        gemini_service=gemini_service,
    )


@pytest.mark.asyncio
async def test_handle_mention_passes_attributed_history_to_gemini(
    ai_chat_service: AiChatService,
    gemini_service: MagicMock,
) -> None:
    captured: dict[str, GeminiRequest] = {}

    async def capture_stream(request: GeminiRequest) -> AsyncIterator[str]:
        captured["request"] = request
        yield "Use Redis."

    gemini_service.stream_response = capture_stream

    async def broadcast(_payload: dict) -> None:
        return None

    await ai_chat_service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=TRIGGER_MESSAGE,
        broadcast=broadcast,
    )

    request = captured["request"]
    history = request.conversation_context.conversation_history
    assert "Sarah: We should evaluate Redis." in history
    assert "Mike: Latency matters for this feature." in history
    assert "partial..." not in history
    assert request.room_id == "room-1"
    assert request.organization_id == "org-a"
    assert request.room_name == "Engineering"


@pytest.mark.asyncio
async def test_handle_mention_loads_messages_from_triggering_room_only(
    ai_chat_service: AiChatService,
    message_repository: MagicMock,
    gemini_service: MagicMock,
) -> None:
    async def empty_stream(_request: GeminiRequest) -> AsyncIterator[str]:
        if False:
            yield ""

    gemini_service.stream_response = empty_stream

    async def broadcast(_payload: dict) -> None:
        return None

    await ai_chat_service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=TRIGGER_MESSAGE,
        broadcast=broadcast,
    )

    message_repository.get_messages.assert_called_once_with("org-a", "room-1", limit=30)


def test_duplicate_identical_message_allowed_after_ttl_expires() -> None:
    room_repository = MagicMock()
    user_repository = MagicMock()
    message_repository = MagicMock()
    authorization_service = RoomAuthorizationService(
        room_repository=room_repository,
        user_repository=user_repository,
    )
    message_service = MessageService(
        message_repository=message_repository,
        room_authorization_service=authorization_service,
    )

    room = MagicMock()
    room.member_ids = ["user-a"]
    room_repository.get_room.return_value = room

    first_message = Message(
        id="message-1",
        sender_id="user-a",
        sender_name="Sarah",
        type="user",
        content="Hello team",
        created_at=CREATED_AT,
        status="complete",
    )
    second_message = Message(
        id="message-2",
        sender_id="user-a",
        sender_name="Sarah",
        type="user",
        content="Hello team",
        created_at=LATER,
        status="complete",
    )
    message_repository.create_message.side_effect = [first_message, second_message]

    from app.models.auth import CurrentUser

    current_user = CurrentUser(
        id="user-a",
        firebase_uid="firebase-a",
        name="Sarah",
        email="sarah@acme.test",
        organization_id="org-a",
        role="member",
    )

    with patch("app.services.message_service.time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = 1000.0
        first = message_service.send_user_message(current_user, "room-1", "Hello team")
        mock_monotonic.return_value = 1003.0
        second = message_service.send_user_message(current_user, "room-1", "Hello team")

    assert first.id == "message-1"
    assert second.id == "message-2"
    assert message_repository.create_message.call_count == 2
