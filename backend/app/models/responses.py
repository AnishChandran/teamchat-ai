from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.auth import UserSummary
from app.models.domain import Message


class RoomSummary(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class RoomResponse(BaseModel):
    id: str
    name: str
    description: str
    member_ids: list[str] = Field(serialization_alias="memberIds")
    created_by: str = Field(serialization_alias="createdBy")
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class RoomsResponse(BaseModel):
    rooms: list[RoomSummary]


class MessagesResponse(BaseModel):
    messages: list[Message]

    model_config = ConfigDict(populate_by_name=True)


class UsersResponse(BaseModel):
    users: list[UserSummary]
