from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.llm.gemini_service import GeminiService, GeminiServiceError
from app.models.domain import Message
from app.services.ai_chat_service import (
    AI_ERROR_MESSAGE,
    GEMINI_SENDER_ID,
    GEMINI_SENDER_NAME,
    AiChatService,
)

CREATED_AT = datetime(2026, 2, 8, 14, 30, tzinfo=timezone.utc)

USER_MESSAGE = Message(
    id="user-msg-1",
    sender_id="user-a",
    sender_name="Sarah",
    type="user",
    content="@Gemini what caching strategy should we use?",
    created_at=CREATED_AT,
    status="complete",
)

HISTORY_MESSAGE = Message(
    id="history-1",
    sender_id="user-b",
    sender_name="Mike",
    type="user",
    content="We should evaluate Redis.",
    created_at=CREATED_AT,
    status="complete",
)


async def successful_stream(*args, **kwargs) -> AsyncIterator[str]:
    for text in ["Redis ", "works well."]:
        yield text


@pytest.fixture
def message_repository() -> MagicMock:
    repository = MagicMock()
    repository.allocate_message_id.return_value = "ai-msg-1"
    repository.get_messages.return_value = [HISTORY_MESSAGE, USER_MESSAGE]
    repository.create_message_with_id.return_value = Message(
        id="ai-msg-1",
        sender_id=GEMINI_SENDER_ID,
        sender_name=GEMINI_SENDER_NAME,
        type="ai",
        content="Redis works well.",
        created_at=CREATED_AT,
        status="complete",
    )
    return repository


@pytest.fixture
def gemini_service() -> MagicMock:
    service = MagicMock(spec=GeminiService)
    service.stream_response = successful_stream
    return service


@pytest.fixture
def ai_chat_service(message_repository: MagicMock, gemini_service: MagicMock) -> AiChatService:
    return AiChatService(
        message_repository=message_repository,
        gemini_service=gemini_service,
    )


@pytest.mark.asyncio
async def test_handle_mention_broadcasts_ai_lifecycle(
    ai_chat_service: AiChatService,
    message_repository: MagicMock,
) -> None:
    broadcasts: list[dict] = []

    async def broadcast(payload: dict) -> None:
        broadcasts.append(payload)

    await ai_chat_service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=USER_MESSAGE,
        broadcast=broadcast,
    )

    assert [event["type"] for event in broadcasts] == [
        "ai_started",
        "ai_chunk",
        "ai_chunk",
        "ai_completed",
    ]
    assert broadcasts[0]["payload"] == {"roomId": "room-1", "messageId": "ai-msg-1"}
    assert broadcasts[1]["payload"]["delta"] == "Redis "
    assert broadcasts[2]["payload"]["delta"] == "works well."
    assert broadcasts[3]["payload"] == {"roomId": "room-1", "messageId": "ai-msg-1"}

    message_repository.get_messages.assert_called_once_with("org-a", "room-1", limit=30)
    message_repository.create_message_with_id.assert_called_once()
    create_kwargs = message_repository.create_message_with_id.call_args.kwargs
    assert create_kwargs["sender_id"] == GEMINI_SENDER_ID
    assert create_kwargs["sender_name"] == GEMINI_SENDER_NAME
    assert create_kwargs["type"] == "ai"
    assert create_kwargs["content"] == "Redis works well."
    assert create_kwargs["status"] == "complete"


@pytest.mark.asyncio
async def test_handle_mention_uses_same_message_id_for_all_events(
    ai_chat_service: AiChatService,
) -> None:
    broadcasts: list[dict] = []

    async def broadcast(payload: dict) -> None:
        broadcasts.append(payload)

    await ai_chat_service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=USER_MESSAGE,
        broadcast=broadcast,
    )

    message_ids = {
        event["payload"]["messageId"]
        for event in broadcasts
        if "payload" in event
    }
    assert message_ids == {"ai-msg-1"}


@pytest.mark.asyncio
async def test_handle_mention_broadcasts_ai_error_on_gemini_failure(
    message_repository: MagicMock,
) -> None:
    gemini_service = MagicMock(spec=GeminiService)

    async def failing_stream(*args, **kwargs) -> AsyncIterator[str]:
        raise GeminiServiceError(
            code="unavailable",
            message="Gemini service unavailable",
            retryable=True,
        )
        yield "unused"

    gemini_service.stream_response = failing_stream
    service = AiChatService(
        message_repository=message_repository,
        gemini_service=gemini_service,
    )
    broadcasts: list[dict] = []

    async def broadcast(payload: dict) -> None:
        broadcasts.append(payload)

    await service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=USER_MESSAGE,
        broadcast=broadcast,
    )

    assert broadcasts[0]["type"] == "ai_started"
    assert broadcasts[-1] == {
        "type": "ai_error",
        "payload": {
            "roomId": "room-1",
            "messageId": "ai-msg-1",
            "message": AI_ERROR_MESSAGE,
        },
    }
    message_repository.create_message_with_id.assert_not_called()


@pytest.mark.asyncio
async def test_handle_mention_does_not_raise_on_unexpected_error(
    message_repository: MagicMock,
) -> None:
    gemini_service = MagicMock(spec=GeminiService)

    async def exploding_stream(*args, **kwargs) -> AsyncIterator[str]:
        raise RuntimeError("boom")
        yield "unused"

    gemini_service.stream_response = exploding_stream
    service = AiChatService(
        message_repository=message_repository,
        gemini_service=gemini_service,
    )
    broadcasts: list[dict] = []

    async def broadcast(payload: dict) -> None:
        broadcasts.append(payload)

    await service.handle_mention(
        organization_id="org-a",
        room_id="room-1",
        room_name="Engineering",
        triggering_message=USER_MESSAGE,
        broadcast=broadcast,
    )

    assert broadcasts[-1]["type"] == "ai_error"
