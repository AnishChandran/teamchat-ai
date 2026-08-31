import asyncio
import json
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.llm.mention_detector import contains_ai_mention
from app.models.auth import CurrentUser
from app.models.events import (
    ErrorEvent,
    JoinRoomEvent,
    LeaveRoomEvent,
    MessageCreatedEvent,
    RoomJoinedEvent,
    RoomLeftEvent,
    SendMessageEvent,
    TypingEvent,
)
from app.repositories.room_repository import RoomNotFoundError
from app.services.ai_chat_service import AiChatService
from app.services.message_service import MessageService, MessageValidationError
from app.services.presence_service import PresenceService
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService
from app.services.typing_service import TypingService
from app.websocket.connection_manager import ConnectionManager

_client_event_adapter: TypeAdapter[Any] = TypeAdapter(
    JoinRoomEvent | LeaveRoomEvent | SendMessageEvent | TypingEvent,
)


class WebSocketRoomEventHandler:
    def __init__(
        self,
        *,
        connection_id: str,
        current_user: CurrentUser,
        connection_manager: ConnectionManager,
        room_authorization_service: RoomAuthorizationService | None = None,
        message_service: MessageService | None = None,
        presence_service: PresenceService | None = None,
        typing_service: TypingService | None = None,
        ai_chat_service: AiChatService | None = None,
    ) -> None:
        self._connection_id = connection_id
        self._current_user = current_user
        self._connection_manager = connection_manager
        self._room_authorization_service = room_authorization_service or RoomAuthorizationService()
        self._message_service = message_service or MessageService(
            room_authorization_service=self._room_authorization_service,
        )
        self._presence_service = presence_service or PresenceService(connection_manager)
        self._typing_service = typing_service or TypingService(connection_manager)
        self._ai_chat_service = ai_chat_service or AiChatService()

    async def handle_message(self, raw_message: str) -> None:
        try:
            payload = json.loads(raw_message)
            event = _client_event_adapter.validate_python(payload)
        except (json.JSONDecodeError, ValidationError):
            await self._send_error("Invalid event payload")
            return

        try:
            if isinstance(event, JoinRoomEvent):
                await self._handle_join_room(event)
                return

            if isinstance(event, LeaveRoomEvent):
                await self._handle_leave_room(event)
                return

            if isinstance(event, SendMessageEvent):
                await self._handle_send_message(event)
                return

            if isinstance(event, TypingEvent):
                await self._handle_typing(event)
                return
        except Exception:
            await self._send_error("Something went wrong. Please try again.")

    async def _handle_join_room(self, event: JoinRoomEvent) -> None:
        try:
            self._room_authorization_service.get_room_for_user(self._current_user, event.room_id)
        except RoomNotFoundError:
            await self._send_error("Room not found", room_id=event.room_id)
            return
        except RoomAccessDeniedError:
            await self._send_error("Room membership is required for this action", room_id=event.room_id)
            return

        self._connection_manager.join_room(
            self._connection_id,
            self._current_user.organization_id,
            event.room_id,
        )
        await self._send_event(
            RoomJoinedEvent(type="room_joined", room_id=event.room_id),
        )
        await self._presence_service.broadcast_room_presence(
            self._current_user.organization_id,
            event.room_id,
        )

    async def _handle_leave_room(self, event: LeaveRoomEvent) -> None:
        self._typing_service.clear_user_in_room(
            self._current_user.organization_id,
            event.room_id,
            self._current_user.id,
        )
        self._connection_manager.leave_room(
            self._connection_id,
            self._current_user.organization_id,
            event.room_id,
        )
        await self._typing_service.broadcast_typing(
            self._current_user.organization_id,
            event.room_id,
        )
        await self._presence_service.broadcast_room_presence(
            self._current_user.organization_id,
            event.room_id,
        )
        await self._send_event(
            RoomLeftEvent(type="room_left", room_id=event.room_id),
        )

    async def _handle_typing(self, event: TypingEvent) -> None:
        room_key = (self._current_user.organization_id, event.room_id)
        connection = self._connection_manager.get_connection(self._connection_id)
        if connection is None or room_key not in connection.room_keys:
            await self._send_error("Join the room before sending typing updates", room_id=event.room_id)
            return

        try:
            self._room_authorization_service.get_room_for_user(self._current_user, event.room_id)
        except RoomNotFoundError:
            await self._send_error("Room not found", room_id=event.room_id)
            return
        except RoomAccessDeniedError:
            await self._send_error("Room membership is required for this action", room_id=event.room_id)
            return

        await self._typing_service.set_typing(
            self._current_user.organization_id,
            event.room_id,
            self._current_user.id,
            self._current_user.name,
            event.is_typing,
            self._connection_id,
        )

    async def _handle_send_message(self, event: SendMessageEvent) -> None:
        try:
            message = self._message_service.send_user_message(
                self._current_user,
                event.room_id,
                event.content,
            )
        except MessageValidationError as exc:
            await self._send_error(str(exc), room_id=event.room_id)
            return
        except RoomNotFoundError:
            await self._send_error("Room not found", room_id=event.room_id)
            return
        except RoomAccessDeniedError:
            await self._send_error("Room membership is required for this action", room_id=event.room_id)
            return
        except Exception:
            await self._send_error("Unable to save message. Please try again.", room_id=event.room_id)
            return

        await self._connection_manager.broadcast_to_room(
            self._current_user.organization_id,
            event.room_id,
            self._serialize_event(
                MessageCreatedEvent(type="message_created", message=message),
            ),
        )

        if not contains_ai_mention(message.content):
            return

        try:
            room = self._room_authorization_service.get_room_for_user(
                self._current_user,
                event.room_id,
            )
        except (RoomNotFoundError, RoomAccessDeniedError):
            return

        organization_id = self._current_user.organization_id
        room_id = event.room_id

        async def broadcast_ai_event(payload: dict) -> None:
            await self._connection_manager.broadcast_to_room(
                organization_id,
                room_id,
                payload,
            )

        asyncio.create_task(
            self._ai_chat_service.handle_mention(
                organization_id=organization_id,
                room_id=room_id,
                room_name=room.name,
                triggering_message=message,
                broadcast=broadcast_ai_event,
            )
        )

    async def _send_error(self, message: str, room_id: str | None = None) -> None:
        await self._send_event(ErrorEvent(type="error", message=message, room_id=room_id))

    async def _send_event(self, event: BaseModel) -> None:
        await self._connection_manager.send_to_connection(
            self._connection_id,
            self._serialize_event(event),
        )

    @staticmethod
    def _serialize_event(event: BaseModel) -> dict:
        return event.model_dump(by_alias=True, mode="json")
