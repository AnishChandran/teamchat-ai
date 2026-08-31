from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class User(BaseModel):
    id: str
    firebase_uid: str = Field(alias="firebaseUid")
    name: str
    email: str
    role: Literal["admin", "member"]
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class Room(BaseModel):
    id: str
    name: str
    description: str
    member_ids: list[str] = Field(alias="memberIds")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class Message(BaseModel):
    id: str
    sender_id: str = Field(alias="senderId")
    sender_name: str = Field(alias="senderName")
    type: Literal["user", "ai", "system"]
    content: str
    created_at: datetime = Field(alias="createdAt")
    status: Literal["streaming", "complete", "error"]

    model_config = {"populate_by_name": True}
