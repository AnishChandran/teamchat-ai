from datetime import datetime
from typing import Literal

from google.cloud import firestore

from app.core.firestore import get_firestore_client
from app.models.domain import Message
from app.repositories.firestore_utils import messages_collection, serialize_document


class MessageRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> firestore.Client:
        if self._client is None:
            return get_firestore_client()
        return self._client

    def get_messages(
        self,
        organization_id: str,
        room_id: str,
        limit: int = 50,
    ) -> list[Message]:
        query = (
            messages_collection(self.client, organization_id, room_id)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        messages: list[Message] = []
        for doc in query.stream():
            data = serialize_document(doc)
            messages.append(Message.model_validate({"id": doc.id, **data}))
        messages.reverse()
        return messages

    def get_message(
        self,
        organization_id: str,
        room_id: str,
        message_id: str,
    ) -> Message | None:
        doc = (
            messages_collection(self.client, organization_id, room_id)
            .document(message_id)
            .get()
        )
        if not doc.exists:
            return None

        data = serialize_document(doc)
        return Message.model_validate({"id": doc.id, **data})

    def allocate_message_id(self, organization_id: str, room_id: str) -> str:
        return messages_collection(self.client, organization_id, room_id).document().id

    def create_message_with_id(
        self,
        organization_id: str,
        room_id: str,
        message_id: str,
        *,
        sender_id: str,
        sender_name: str,
        type: Literal["user", "ai", "system"],
        content: str,
        status: Literal["streaming", "complete", "error"],
        created_at: datetime,
    ) -> Message:
        doc_ref = messages_collection(self.client, organization_id, room_id).document(message_id)
        message_data = {
            "senderId": sender_id,
            "senderName": sender_name,
            "type": type,
            "content": content,
            "status": status,
            "createdAt": created_at,
        }
        doc_ref.set(message_data)
        return Message.model_validate({"id": message_id, **message_data})

    def create_message(
        self,
        organization_id: str,
        room_id: str,
        *,
        sender_id: str,
        sender_name: str,
        type: Literal["user", "ai", "system"],
        content: str,
        status: Literal["streaming", "complete", "error"],
        created_at: datetime,
    ) -> Message:
        doc_ref = messages_collection(self.client, organization_id, room_id).document()
        message_data = {
            "senderId": sender_id,
            "senderName": sender_name,
            "type": type,
            "content": content,
            "status": status,
            "createdAt": created_at,
        }
        doc_ref.set(message_data)
        return Message.model_validate({"id": doc_ref.id, **message_data})
