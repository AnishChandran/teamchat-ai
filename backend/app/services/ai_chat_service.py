from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from app.llm.context_builder import build_conversation_context
from app.llm.gemini_service import GeminiRequest, GeminiService, GeminiServiceError
from app.models.domain import Message
from app.models.events import (
    AiChunkEvent,
    AiChunkPayload,
    AiCompletedEvent,
    AiCompletedPayload,
    AiErrorEvent,
    AiErrorPayload,
    AiStartedEvent,
    AiStartedPayload,
)
from app.repositories.message_repository import MessageRepository

GEMINI_SENDER_ID = "gemini"
GEMINI_SENDER_NAME = "Gemini"
AI_CONTEXT_MESSAGE_LIMIT = 30
AI_ERROR_MESSAGE = "AI is temporarily unavailable. Please try again."

BroadcastFn = Callable[[dict], Awaitable[None]]


class AiChatService:
    def __init__(
        self,
        *,
        message_repository: MessageRepository | None = None,
        gemini_service: GeminiService | None = None,
    ) -> None:
        self._message_repository = message_repository or MessageRepository()
        self._gemini_service = gemini_service or GeminiService()

    async def handle_mention(
        self,
        *,
        organization_id: str,
        room_id: str,
        room_name: str | None,
        triggering_message: Message,
        broadcast: BroadcastFn,
    ) -> None:
        message_id = self._message_repository.allocate_message_id(organization_id, room_id)

        try:
            await broadcast(
                AiStartedEvent(
                    type="ai_started",
                    payload=AiStartedPayload(room_id=room_id, message_id=message_id),
                ).model_dump(by_alias=True, mode="json"),
            )

            messages = self._message_repository.get_messages(
                organization_id,
                room_id,
                limit=AI_CONTEXT_MESSAGE_LIMIT,
            )
            conversation_context = build_conversation_context(messages)
            final_content = await self._stream_response(
                organization_id=organization_id,
                room_id=room_id,
                room_name=room_name,
                conversation_context=conversation_context,
                triggering_message=triggering_message.content,
                message_id=message_id,
                broadcast=broadcast,
            )

            self._message_repository.create_message_with_id(
                organization_id,
                room_id,
                message_id,
                sender_id=GEMINI_SENDER_ID,
                sender_name=GEMINI_SENDER_NAME,
                type="ai",
                content=final_content,
                status="complete",
                created_at=datetime.now(timezone.utc),
            )

            await broadcast(
                AiCompletedEvent(
                    type="ai_completed",
                    payload=AiCompletedPayload(room_id=room_id, message_id=message_id),
                ).model_dump(by_alias=True, mode="json"),
            )
        except GeminiServiceError:
            await broadcast(
                AiErrorEvent(
                    type="ai_error",
                    payload=AiErrorPayload(
                        room_id=room_id,
                        message_id=message_id,
                        message=AI_ERROR_MESSAGE,
                    ),
                ).model_dump(by_alias=True, mode="json"),
            )
        except Exception:
            await broadcast(
                AiErrorEvent(
                    type="ai_error",
                    payload=AiErrorPayload(
                        room_id=room_id,
                        message_id=message_id,
                        message=AI_ERROR_MESSAGE,
                    ),
                ).model_dump(by_alias=True, mode="json"),
            )

    async def _stream_response(
        self,
        *,
        organization_id: str,
        room_id: str,
        room_name: str | None,
        conversation_context,
        triggering_message: str,
        message_id: str,
        broadcast: BroadcastFn,
    ) -> str:
        request = GeminiRequest(
            organization_id=organization_id,
            room_id=room_id,
            room_name=room_name,
            conversation_context=conversation_context,
            triggering_message=triggering_message,
        )
        chunks: list[str] = []
        async for delta in self._gemini_service.stream_response(request):
            chunks.append(delta)
            await broadcast(
                AiChunkEvent(
                    type="ai_chunk",
                    payload=AiChunkPayload(
                        room_id=room_id,
                        message_id=message_id,
                        delta=delta,
                    ),
                ).model_dump(by_alias=True, mode="json"),
            )
        return "".join(chunks)
