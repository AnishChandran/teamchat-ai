import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.auth import CurrentUser
from app.models.domain import Message
from app.repositories.message_repository import MessageRepository
from app.repositories.room_repository import RoomNotFoundError
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService

DEDUP_TTL_SECONDS = 2.0


class MessageValidationError(Exception):
    """Raised when message content is invalid."""


@dataclass(frozen=True)
class _DedupEntry:
    message: Message
    expires_at: float


class MessageService:
    def __init__(
        self,
        message_repository: MessageRepository | None = None,
        room_authorization_service: RoomAuthorizationService | None = None,
    ) -> None:
        self._message_repository = message_repository or MessageRepository()
        self._room_authorization_service = room_authorization_service or RoomAuthorizationService()
        self._recent_messages: dict[tuple[str, str, str], _DedupEntry] = {}

    def send_user_message(
        self,
        current_user: CurrentUser,
        room_id: str,
        content: str,
    ) -> Message:
        normalized_content = content.strip()
        if not normalized_content:
            raise MessageValidationError("Message content cannot be empty")

        self._room_authorization_service.get_room_for_user(current_user, room_id)

        dedup_key = (current_user.id, room_id, normalized_content)
        cached = self._recent_messages.get(dedup_key)
        now = time.monotonic()
        if cached is not None and cached.expires_at > now:
            return cached.message

        message = self._message_repository.create_message(
            current_user.organization_id,
            room_id,
            sender_id=current_user.id,
            sender_name=current_user.name,
            type="user",
            content=normalized_content,
            status="complete",
            created_at=datetime.now(timezone.utc),
        )
        self._recent_messages[dedup_key] = _DedupEntry(
            message=message,
            expires_at=now + DEDUP_TTL_SECONDS,
        )
        self._prune_expired(now)
        return message

    def _prune_expired(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._recent_messages.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._recent_messages.pop(key, None)


# Re-export authorization errors for callers.
__all__ = [
    "MessageService",
    "MessageValidationError",
    "RoomNotFoundError",
    "RoomAccessDeniedError",
]
