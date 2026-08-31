from datetime import datetime
from typing import Any

from google.cloud import firestore


def serialize_document(doc: firestore.DocumentSnapshot) -> dict[str, Any]:
    data = doc.to_dict() or {}
    created_at = data.get("createdAt")
    if isinstance(created_at, datetime):
        data["createdAt"] = created_at
    return data


def organization_document(
    client: firestore.Client,
    organization_id: str,
) -> firestore.DocumentReference:
    return client.collection("organizations").document(organization_id)


def users_collection(
    client: firestore.Client,
    organization_id: str,
) -> firestore.CollectionReference:
    return organization_document(client, organization_id).collection("users")


def rooms_collection(
    client: firestore.Client,
    organization_id: str,
) -> firestore.CollectionReference:
    return organization_document(client, organization_id).collection("rooms")


def messages_collection(
    client: firestore.Client,
    organization_id: str,
    room_id: str,
) -> firestore.CollectionReference:
    return rooms_collection(client, organization_id).document(room_id).collection("messages")
