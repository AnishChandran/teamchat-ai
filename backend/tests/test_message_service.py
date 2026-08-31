from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.auth import CurrentUser
from app.models.domain import Message, Room
from app.repositories.room_repository import RoomNotFoundError
from app.services.message_service import MessageService, MessageValidationError
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

CURRENT_USER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Org A Member",
    email="a@example.com",
    organization_id="org-a",
    role="member",
)

SAMPLE_ROOM = Room(
    id="room-1",
    name="General",
    description="Team chat",
    member_ids=["user-a"],
    created_by="user-a",
    created_at=CREATED_AT,
)

SAMPLE_MESSAGE = Message(
    id="message-1",
    sender_id="user-a",
    sender_name="Org A Member",
    type="user",
    content="Hello team",
    created_at=CREATED_AT,
    status="complete",
)


@pytest.fixture
def message_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def room_authorization_service() -> MagicMock:
    return MagicMock(spec=RoomAuthorizationService)


@pytest.fixture
def message_service(
    message_repository: MagicMock,
    room_authorization_service: MagicMock,
) -> MessageService:
    return MessageService(
        message_repository=message_repository,
        room_authorization_service=room_authorization_service,
    )


def test_send_user_message_persists_message(
    message_service: MessageService,
    message_repository: MagicMock,
    room_authorization_service: MagicMock,
) -> None:
    room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM
    message_repository.create_message.return_value = SAMPLE_MESSAGE

    message = message_service.send_user_message(CURRENT_USER, "room-1", "  Hello team  ")

    assert message.id == "message-1"
    assert message.type == "user"
    assert message.status == "complete"
    message_repository.create_message.assert_called_once()
    create_kwargs = message_repository.create_message.call_args.kwargs
    assert create_kwargs["content"] == "Hello team"
    assert create_kwargs["sender_name"] == "Org A Member"


def test_send_user_message_rejects_empty_content(message_service: MessageService) -> None:
    with pytest.raises(MessageValidationError):
        message_service.send_user_message(CURRENT_USER, "room-1", "   ")


def test_send_user_message_rejects_non_member(
    message_service: MessageService,
    room_authorization_service: MagicMock,
    message_repository: MagicMock,
) -> None:
    room_authorization_service.get_room_for_user.side_effect = RoomAccessDeniedError(
        "Room membership is required for this action"
    )

    with pytest.raises(RoomAccessDeniedError):
        message_service.send_user_message(CURRENT_USER, "room-1", "Hello")

    message_repository.create_message.assert_not_called()


def test_send_user_message_rejects_cross_organization_room(
    message_service: MessageService,
    room_authorization_service: MagicMock,
    message_repository: MagicMock,
) -> None:
    room_authorization_service.get_room_for_user.side_effect = RoomNotFoundError(
        "Room 'room-b1' was not found"
    )

    with pytest.raises(RoomNotFoundError):
        message_service.send_user_message(CURRENT_USER, "room-b1", "Hello")

    message_repository.create_message.assert_not_called()


def test_send_user_message_deduplicates_repeated_events(
    message_service: MessageService,
    message_repository: MagicMock,
    room_authorization_service: MagicMock,
) -> None:
    room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM
    message_repository.create_message.return_value = SAMPLE_MESSAGE

    first = message_service.send_user_message(CURRENT_USER, "room-1", "Hello team")
    second = message_service.send_user_message(CURRENT_USER, "room-1", "Hello team")

    assert first.id == second.id
    message_repository.create_message.assert_called_once()
