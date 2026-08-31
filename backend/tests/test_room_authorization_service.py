from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.auth import CurrentUser
from app.models.domain import Room, User
from app.repositories.room_repository import RoomNotFoundError
from app.services.room_authorization_service import (
    RoomAccessDeniedError,
    RoomAuthorizationService,
)

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ADMIN_USER = CurrentUser(
    id="admin-1",
    firebase_uid="firebase-admin",
    name="Admin User",
    email="admin@example.com",
    organization_id="org-1",
    role="admin",
)

MEMBER_USER = CurrentUser(
    id="member-1",
    firebase_uid="firebase-member",
    name="Member User",
    email="member@example.com",
    organization_id="org-1",
    role="member",
)

OTHER_ORG_USER = CurrentUser(
    id="admin-2",
    firebase_uid="firebase-admin-2",
    name="Other Admin",
    email="other@example.com",
    organization_id="org-2",
    role="admin",
)

SAMPLE_ROOM = Room(
    id="room-1",
    name="General",
    description="Team chat",
    member_ids=["admin-1", "member-1"],
    created_by="admin-1",
    created_at=CREATED_AT,
)

NON_MEMBER_ROOM = Room(
    id="room-2",
    name="Private",
    description="Admins only",
    member_ids=["admin-1"],
    created_by="admin-1",
    created_at=CREATED_AT,
)


@pytest.fixture
def room_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(room_repository: MagicMock, user_repository: MagicMock) -> RoomAuthorizationService:
    return RoomAuthorizationService(
        room_repository=room_repository,
        user_repository=user_repository,
    )


def test_get_room_for_user_allows_member_in_same_organization(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = SAMPLE_ROOM

    room = service.get_room_for_user(MEMBER_USER, "room-1")

    assert room.id == "room-1"
    room_repository.get_room.assert_called_once_with("org-1", "room-1")


def test_get_room_for_user_denies_non_member(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = NON_MEMBER_ROOM

    with pytest.raises(RoomAccessDeniedError):
        service.get_room_for_user(MEMBER_USER, "room-2")


def test_get_room_for_user_denies_cross_organization_access(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = None

    with pytest.raises(RoomNotFoundError):
        service.get_room_for_user(OTHER_ORG_USER, "room-1")

    room_repository.get_room.assert_called_once_with("org-2", "room-1")


def test_list_rooms_for_user_uses_current_user_organization_and_id(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.list_rooms_for_user.return_value = [SAMPLE_ROOM]

    rooms = service.list_rooms_for_user(MEMBER_USER)

    assert rooms == [SAMPLE_ROOM]
    room_repository.list_rooms_for_user.assert_called_once_with("org-1", "member-1")


def test_create_room_allows_admin(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_id.return_value = User(
        id="member-1",
        firebase_uid="firebase-member",
        name="Member User",
        email="member@example.com",
        role="member",
        created_at=CREATED_AT,
    )
    room_repository.create_room.return_value = SAMPLE_ROOM

    room = service.create_room(
        ADMIN_USER,
        name="General",
        description="Team chat",
        member_ids=["member-1"],
    )

    assert room.id == "room-1"
    room_repository.create_room.assert_called_once()
    create_kwargs = room_repository.create_room.call_args.kwargs
    assert create_kwargs["name"] == "General"
    assert create_kwargs["member_ids"] == ["member-1", "admin-1"]


def test_create_room_denies_member(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    with pytest.raises(RoomAccessDeniedError):
        service.create_room(
            MEMBER_USER,
            name="General",
            description="Team chat",
        )

    room_repository.create_room.assert_not_called()


def test_add_member_allows_admin_for_user_in_same_organization(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = SAMPLE_ROOM
    user_repository.get_user_by_id.return_value = User(
        id="member-2",
        firebase_uid="firebase-member-2",
        name="Member Two",
        email="member2@example.com",
        role="member",
        created_at=CREATED_AT,
    )
    updated_room = SAMPLE_ROOM.model_copy(update={"member_ids": ["admin-1", "member-1", "member-2"]})
    room_repository.add_member.return_value = updated_room

    room = service.add_member(ADMIN_USER, "room-1", "member-2")

    assert "member-2" in room.member_ids
    room_repository.add_member.assert_called_once_with("org-1", "room-1", "member-2")


def test_add_member_denies_member_role(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> None:
    with pytest.raises(RoomAccessDeniedError):
        service.add_member(MEMBER_USER, "room-1", "member-2")

    room_repository.add_member.assert_not_called()
    user_repository.get_user_by_id.assert_not_called()


def test_add_member_denies_user_outside_organization(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
    user_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = SAMPLE_ROOM
    user_repository.get_user_by_id.return_value = None

    with pytest.raises(RoomAccessDeniedError):
        service.add_member(ADMIN_USER, "room-1", "outside-user")

    room_repository.add_member.assert_not_called()


def test_remove_member_allows_admin(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    room_repository.get_room.return_value = SAMPLE_ROOM
    updated_room = SAMPLE_ROOM.model_copy(update={"member_ids": ["admin-1"]})
    room_repository.remove_member.return_value = updated_room

    room = service.remove_member(ADMIN_USER, "room-1", "member-1")

    assert room.member_ids == ["admin-1"]
    room_repository.remove_member.assert_called_once_with("org-1", "room-1", "member-1")


def test_remove_member_denies_member_role(
    service: RoomAuthorizationService,
    room_repository: MagicMock,
) -> None:
    with pytest.raises(RoomAccessDeniedError):
        service.remove_member(MEMBER_USER, "room-1", "admin-1")

    room_repository.remove_member.assert_not_called()
