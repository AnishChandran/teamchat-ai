from app.models.events import PresencePayload, PresenceUpdatedEvent
from app.websocket.connection_manager import ConnectionManager


class PresenceService:
    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def broadcast_room_presence(self, organization_id: str, room_id: str) -> None:
        users = self._connection_manager.get_room_presence_users(organization_id, room_id)
        event = PresenceUpdatedEvent(
            type="presence_updated",
            payload=PresencePayload(room_id=room_id, users=users),
        )
        await self._connection_manager.broadcast_to_room(
            organization_id,
            room_id,
            event.model_dump(by_alias=True, mode="json"),
        )
