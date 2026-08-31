from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.auth import CurrentUser
from app.models.domain import Room, User
from app.repositories.room_repository import RoomNotFoundError
from app.services.message_service import MessageService
from app.services.room_authorization_service import (
    RoomAccessDeniedError,
    RoomAuthorizationService,
)

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ORG_A_MEMBER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Sarah",
    email="sarah@acme.test",
    organization_id="org-a",
    role="member",
)

ORG_B_MEMBER = CurrentUser(
    id="user-b",
    firebase_uid="firebase-b",
    name="John",
    email="john@globex.test",
    organization_id="org-b",
    role="member",
)

ORG_A_ADMIN = CurrentUser(
    id="admin-a",
    firebase_uid="firebase-admin-a",
    name="Admin",
    email="admin@acme.test",
    organization_id="org-a",
    role="admin",
)

MEMBER_ROOM = Room(
    id="room-1",
    name="General",
    description="Team chat",
    member_ids=["user-a", "admin-a"],
    created_by="admin-a",
    created_at=CREATED_AT,
)

PRIVATE_ROOM = Room(
    id="room-private",
    name="Private",
    description="Admins only",
    member_ids=["admin-a"],
    created_by="admin-a",
    created_at=CREATED_AT,
)


@pytest.fixture
def room_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def authorization_service(
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> RoomAuthorizationService:
    return RoomAuthorizationService(
        room_repository=room_repository,
        user_repository=user_repository,
    )


@pytest.fixture
def message_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def message_service(
    message_repository: MagicMock,
    authorization_service: RoomAuthorizationService,
) -> MessageService:
    return MessageService(
        message_repository=message_repository,
        room_authorization_service=authorization_service,
    )


def test_room_lookup_always_scoped_to_authenticated_organization(
    authorization_service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = None

    with pytest.raises(RoomNotFoundError):
        authorization_service.get_room_for_user(ORG_B_MEMBER, "room-1")

    room_repository.get_room.assert_called_once_with("org-b", "room-1")


def test_non_member_cannot_persist_message_to_restricted_room(
    message_service: MessageService,
    room_repository: MagicMock,
    message_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = PRIVATE_ROOM

    with pytest.raises(RoomAccessDeniedError):
        message_service.send_user_message(ORG_A_MEMBER, "room-private", "Hello")

    message_repository.create_message.assert_not_called()


def test_cross_org_room_id_does_not_persist_message(
    message_service: MessageService,
    room_repository: MagicMock,
    message_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = None

    with pytest.raises(RoomNotFoundError):
        message_service.send_user_message(ORG_A_MEMBER, "room-b1", "Hello")

    message_repository.create_message.assert_not_called()


def test_persisted_message_sender_matches_authenticated_user(
    message_service: MessageService,
    room_repository: MagicMock,
    message_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = MEMBER_ROOM
    message_repository.create_message.return_value = MagicMock(id="message-1")

    message_service.send_user_message(ORG_A_MEMBER, "room-1", "Hello team")

    org_id, room_id = message_repository.create_message.call_args.args
    create_kwargs = message_repository.create_message.call_args.kwargs
    assert org_id == "org-a"
    assert room_id == "room-1"
    assert create_kwargs["sender_id"] == "user-a"
    assert create_kwargs["sender_name"] == "Sarah"
    assert create_kwargs["type"] == "user"


def test_member_cannot_create_room_at_service_layer(
    authorization_service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    with pytest.raises(RoomAccessDeniedError):
        authorization_service.create_room(
            ORG_A_MEMBER,
            name="New Room",
            description="Should fail",
        )

    room_repository.create_room.assert_not_called()


def test_admin_create_room_always_includes_creator_in_members(
    authorization_service: RoomAuthorizationService,
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_id.return_value = User(
        id="user-a",
        firebase_uid="firebase-a",
        name="Sarah",
        email="sarah@acme.test",
        role="member",
        created_at=CREATED_AT,
    )
    room_repository.create_room.return_value = MEMBER_ROOM

    authorization_service.create_room(
        ORG_A_ADMIN,
        name="Project Alpha",
        description="New project room",
        member_ids=["user-a"],
    )

    org_id = room_repository.create_room.call_args.args[0]
    create_kwargs = room_repository.create_room.call_args.kwargs
    assert org_id == "org-a"
    assert create_kwargs["created_by"] == "admin-a"
    assert create_kwargs["member_ids"] == ["user-a", "admin-a"]
