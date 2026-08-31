import asyncio
import time
from dataclasses import dataclass

from app.models.events import PresenceUser, TypingPayload, TypingUpdatedEvent
from app.websocket.connection_manager import ConnectionManager

DEFAULT_TYPING_TTL_SECONDS = 5.0


@dataclass
class _TypingEntry:
    user_name: str
    expires_at: float


class TypingService:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        *,
        ttl_seconds: float = DEFAULT_TYPING_TTL_SECONDS,
    ) -> None:
        self._connection_manager = connection_manager
        self._ttl_seconds = ttl_seconds
        self._entries: dict[tuple[str, str, str], _TypingEntry] = {}
        self._expiry_tokens: dict[tuple[str, str, str], int] = {}

    async def set_typing(
        self,
        organization_id: str,
        room_id: str,
        user_id: str,
        user_name: str,
        is_typing: bool,
        connection_id: str,
    ) -> None:
        key = (organization_id, room_id, user_id)
        if not is_typing:
            if key in self._entries:
                self._entries.pop(key)
                self._bump_expiry_token(key)
            await self.broadcast_typing(
                organization_id,
                room_id,
                exclude_connection_id=connection_id,
            )
            return

        self._bump_expiry_token(key)
        token = self._expiry_tokens[key]
        self._entries[key] = _TypingEntry(
            user_name=user_name,
            expires_at=time.monotonic() + self._ttl_seconds,
        )
        asyncio.create_task(self._expire_after(key, organization_id, room_id, token))
        await self.broadcast_typing(
            organization_id,
            room_id,
            exclude_connection_id=connection_id,
        )

    def clear_user_in_room(self, organization_id: str, room_id: str, user_id: str) -> None:
        key = (organization_id, room_id, user_id)
        if key not in self._entries:
            return
        self._entries.pop(key)
        self._bump_expiry_token(key)

    async def clear_user_in_room_and_broadcast(
        self,
        organization_id: str,
        room_id: str,
        user_id: str,
    ) -> None:
        self.clear_user_in_room(organization_id, room_id, user_id)
        await self.broadcast_typing(organization_id, room_id)

    def get_typing_users(self, organization_id: str, room_id: str) -> list[PresenceUser]:
        now = time.monotonic()
        users_by_id: dict[str, str] = {}
        expired_keys: list[tuple[str, str, str]] = []

        for (org_id, rid, user_id), entry in self._entries.items():
            if org_id != organization_id or rid != room_id:
                continue
            if entry.expires_at <= now:
                expired_keys.append((org_id, rid, user_id))
                continue
            users_by_id[user_id] = entry.user_name

        for key in expired_keys:
            self._entries.pop(key, None)
            self._bump_expiry_token(key)

        return [
            PresenceUser(id=user_id, name=name)
            for user_id, name in sorted(users_by_id.items(), key=lambda item: item[0])
        ]

    async def broadcast_typing(
        self,
        organization_id: str,
        room_id: str,
        *,
        exclude_connection_id: str | None = None,
    ) -> None:
        users = self.get_typing_users(organization_id, room_id)
        event = TypingUpdatedEvent(
            type="typing_updated",
            payload=TypingPayload(room_id=room_id, users=users),
        )
        payload = event.model_dump(by_alias=True, mode="json")
        if exclude_connection_id is not None:
            await self._connection_manager.broadcast_to_room_excluding(
                organization_id,
                room_id,
                exclude_connection_id,
                payload,
            )
            return

        await self._connection_manager.broadcast_to_room(
            organization_id,
            room_id,
            payload,
        )

    def _bump_expiry_token(self, key: tuple[str, str, str]) -> None:
        self._expiry_tokens[key] = self._expiry_tokens.get(key, 0) + 1

    async def _expire_after(
        self,
        key: tuple[str, str, str],
        organization_id: str,
        room_id: str,
        token: int,
    ) -> None:
        await asyncio.sleep(self._ttl_seconds)
        if self._expiry_tokens.get(key) != token:
            return

        entry = self._entries.get(key)
        if entry is None or entry.expires_at > time.monotonic():
            return

        self._entries.pop(key, None)
        await self.broadcast_typing(organization_id, room_id)
