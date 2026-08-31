from datetime import datetime

from google.cloud import firestore

from app.core.firestore import get_firestore_client
from app.models.domain import Room
from app.repositories.firestore_utils import rooms_collection, serialize_document


class RoomNotFoundError(Exception):
    """Raised when a room document does not exist in the organization."""


class RoomRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> firestore.Client:
        if self._client is None:
            return get_firestore_client()
        return self._client

    def get_room(self, organization_id: str, room_id: str) -> Room | None:
        doc = rooms_collection(self.client, organization_id).document(room_id).get()
        if not doc.exists:
            return None

        data = serialize_document(doc)
        return Room.model_validate({"id": doc.id, **data})

    def list_rooms_for_user(self, organization_id: str, user_id: str) -> list[Room]:
        query = (
            rooms_collection(self.client, organization_id)
            .where(filter=firestore.FieldFilter("memberIds", "array_contains", user_id))
        )
        rooms: list[Room] = []
        for doc in query.stream():
            data = serialize_document(doc)
            rooms.append(Room.model_validate({"id": doc.id, **data}))
        return rooms

    def create_room(
        self,
        organization_id: str,
        *,
        name: str,
        description: str,
        member_ids: list[str],
        created_by: str,
        created_at: datetime,
    ) -> Room:
        doc_ref = rooms_collection(self.client, organization_id).document()
        room_data = {
            "name": name,
            "description": description,
            "memberIds": member_ids,
            "createdBy": created_by,
            "createdAt": created_at,
        }
        doc_ref.set(room_data)
        return Room.model_validate({"id": doc_ref.id, **room_data, "createdAt": created_at})

    def add_member(self, organization_id: str, room_id: str, user_id: str) -> Room:
        room = self._get_existing_room(organization_id, room_id)
        if user_id in room.member_ids:
            return room

        updated_member_ids = [*room.member_ids, user_id]
        rooms_collection(self.client, organization_id).document(room_id).update(
            {"memberIds": updated_member_ids}
        )
        return room.model_copy(update={"member_ids": updated_member_ids})

    def remove_member(self, organization_id: str, room_id: str, user_id: str) -> Room:
        room = self._get_existing_room(organization_id, room_id)
        if user_id not in room.member_ids:
            return room

        updated_member_ids = [member_id for member_id in room.member_ids if member_id != user_id]
        rooms_collection(self.client, organization_id).document(room_id).update(
            {"memberIds": updated_member_ids}
        )
        return room.model_copy(update={"member_ids": updated_member_ids})

    def _get_existing_room(self, organization_id: str, room_id: str) -> Room:
        room = self.get_room(organization_id, room_id)
        if room is None:
            raise RoomNotFoundError(f"Room '{room_id}' was not found")
        return room
