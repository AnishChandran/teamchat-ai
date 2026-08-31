import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket

from app.models.auth import CurrentUser
from app.models.connection import ConnectionMetadata
from app.models.events import PresenceUser

logger = logging.getLogger(__name__)


@dataclass
class ActiveConnection:
    websocket: WebSocket
    metadata: ConnectionMetadata
    room_keys: set[tuple[str, str]] = field(default_factory=set)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, ActiveConnection] = {}
        self._room_connections: dict[tuple[str, str], set[str]] = {}

    def register(self, websocket: WebSocket, current_user: CurrentUser) -> ConnectionMetadata:
        connection_id = str(uuid4())
        metadata = ConnectionMetadata(
            connection_id=connection_id,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            user_name=current_user.name,
            connected_at=datetime.now(timezone.utc),
        )
        self._connections[connection_id] = ActiveConnection(
            websocket=websocket,
            metadata=metadata,
        )
        return metadata

    def unregister(self, connection_id: str) -> list[tuple[str, str]]:
        connection = self._connections.pop(connection_id, None)
        if connection is None:
            return []

        affected_rooms = list(connection.room_keys)
        for room_key in connection.room_keys:
            room_connections = self._room_connections.get(room_key)
            if room_connections is None:
                continue
            room_connections.discard(connection_id)
            if not room_connections:
                self._room_connections.pop(room_key, None)

        return affected_rooms

    async def send_to_connection(self, connection_id: str, payload: dict) -> None:
        connection = self._connections.get(connection_id)
        if connection is None:
            return

        try:
            await connection.websocket.send_text(json.dumps(payload))
        except Exception:
            logger.warning("Removing stale WebSocket connection %s", connection_id)
            self.unregister(connection_id)

    async def broadcast_to_room(
        self,
        organization_id: str,
        room_id: str,
        payload: dict,
    ) -> None:
        room_key = (organization_id, room_id)
        connection_ids = list(self._room_connections.get(room_key, set()))
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, payload)

    async def broadcast_to_room_excluding(
        self,
        organization_id: str,
        room_id: str,
        exclude_connection_id: str,
        payload: dict,
    ) -> None:
        room_key = (organization_id, room_id)
        connection_ids = list(self._room_connections.get(room_key, set()))
        for connection_id in connection_ids:
            if connection_id == exclude_connection_id:
                continue
            await self.send_to_connection(connection_id, payload)

    def join_room(self, connection_id: str, organization_id: str, room_id: str) -> None:
        connection = self._connections.get(connection_id)
        if connection is None:
            return

        room_key = (organization_id, room_id)
        connection.room_keys.add(room_key)
        self._room_connections.setdefault(room_key, set()).add(connection_id)

    def leave_room(self, connection_id: str, organization_id: str, room_id: str) -> None:
        connection = self._connections.get(connection_id)
        if connection is None:
            return

        room_key = (organization_id, room_id)
        connection.room_keys.discard(room_key)

        room_connections = self._room_connections.get(room_key)
        if room_connections is None:
            return

        room_connections.discard(connection_id)
        if not room_connections:
            self._room_connections.pop(room_key, None)

    def get_room_presence_users(self, organization_id: str, room_id: str) -> list[PresenceUser]:
        users_by_id: dict[str, str] = {}
        for connection_id in self._room_connections.get((organization_id, room_id), set()):
            connection = self._connections.get(connection_id)
            if connection is None:
                continue
            users_by_id[connection.metadata.user_id] = connection.metadata.user_name

        return [
            PresenceUser(id=user_id, name=name)
            for user_id, name in sorted(users_by_id.items(), key=lambda item: item[0])
        ]

    def get_connection(self, connection_id: str) -> ActiveConnection | None:
        return self._connections.get(connection_id)

    def get_room_connection_ids(self, organization_id: str, room_id: str) -> set[str]:
        return set(self._room_connections.get((organization_id, room_id), set()))
