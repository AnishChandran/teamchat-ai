from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from app.models.domain import Message


# Client → Server


class JoinRoomEvent(BaseModel):
    type: Literal["join_room"]
    room_id: str = Field(alias="roomId")

    model_config = {"populate_by_name": True}


class LeaveRoomEvent(BaseModel):
    type: Literal["leave_room"]
    room_id: str = Field(alias="roomId")

    model_config = {"populate_by_name": True}


class SendMessageEvent(BaseModel):
    type: Literal["send_message"]
    room_id: str = Field(alias="roomId")
    content: str

    model_config = {"populate_by_name": True}


class TypingEvent(BaseModel):
    type: Literal["typing"]
    room_id: str = Field(alias="roomId")
    is_typing: bool = Field(alias="isTyping")

    model_config = {"populate_by_name": True}


ClientEvent = Annotated[
    Union[JoinRoomEvent, LeaveRoomEvent, SendMessageEvent, TypingEvent],
    Field(discriminator="type"),
]


# Server → Client


class MessageCreatedEvent(BaseModel):
    type: Literal["message_created"]
    message: Message


class PresenceUser(BaseModel):
    id: str
    name: str


class PresencePayload(BaseModel):
    room_id: str = Field(alias="roomId")
    users: list[PresenceUser]

    model_config = {"populate_by_name": True}


class PresenceUpdatedEvent(BaseModel):
    type: Literal["presence_updated"]
    payload: PresencePayload

    model_config = {"populate_by_name": True}


class TypingPayload(BaseModel):
    room_id: str = Field(alias="roomId")
    users: list[PresenceUser]

    model_config = {"populate_by_name": True}


class TypingUpdatedEvent(BaseModel):
    type: Literal["typing_updated"]
    payload: TypingPayload

    model_config = {"populate_by_name": True}


class AiStartedPayload(BaseModel):
    room_id: str = Field(alias="roomId")
    message_id: str = Field(alias="messageId")

    model_config = {"populate_by_name": True}


class AiStartedEvent(BaseModel):
    type: Literal["ai_started"]
    payload: AiStartedPayload

    model_config = {"populate_by_name": True}


class AiChunkPayload(BaseModel):
    room_id: str = Field(alias="roomId")
    message_id: str = Field(alias="messageId")
    delta: str

    model_config = {"populate_by_name": True}


class AiChunkEvent(BaseModel):
    type: Literal["ai_chunk"]
    payload: AiChunkPayload

    model_config = {"populate_by_name": True}


class AiCompletedPayload(BaseModel):
    room_id: str = Field(alias="roomId")
    message_id: str = Field(alias="messageId")

    model_config = {"populate_by_name": True}


class AiCompletedEvent(BaseModel):
    type: Literal["ai_completed"]
    payload: AiCompletedPayload

    model_config = {"populate_by_name": True}


class AiErrorPayload(BaseModel):
    room_id: str = Field(alias="roomId")
    message_id: str = Field(alias="messageId")
    message: str

    model_config = {"populate_by_name": True}


class AiErrorEvent(BaseModel):
    type: Literal["ai_error"]
    payload: AiErrorPayload

    model_config = {"populate_by_name": True}


class RoomJoinedEvent(BaseModel):
    type: Literal["room_joined"]
    room_id: str = Field(alias="roomId")

    model_config = {"populate_by_name": True}


class RoomLeftEvent(BaseModel):
    type: Literal["room_left"]
    room_id: str = Field(alias="roomId")

    model_config = {"populate_by_name": True}


class ErrorEvent(BaseModel):
    type: Literal["error"]
    message: str
    room_id: str | None = Field(default=None, alias="roomId")

    model_config = {"populate_by_name": True}


ServerEvent = Annotated[
    Union[
        MessageCreatedEvent,
        PresenceUpdatedEvent,
        TypingUpdatedEvent,
        AiStartedEvent,
        AiChunkEvent,
        AiCompletedEvent,
        AiErrorEvent,
        RoomJoinedEvent,
        RoomLeftEvent,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]
