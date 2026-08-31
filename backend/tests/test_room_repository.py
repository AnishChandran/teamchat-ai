from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.domain import Room
from app.repositories.room_repository import RoomNotFoundError, RoomRepository

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ROOM_DATA = {
    "name": "General",
    "description": "Team chat",
    "memberIds": ["user-1", "user-2"],
    "createdBy": "user-1",
    "createdAt": CREATED_AT,
}


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repository(mock_client: MagicMock) -> RoomRepository:
    return RoomRepository(client=mock_client)


def _rooms_collection(mock_client: MagicMock) -> MagicMock:
    return (
        mock_client.collection.return_value.document.return_value.collection.return_value
    )


def test_get_room_returns_room_when_document_exists(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "room-1"
    doc.to_dict.return_value = ROOM_DATA.copy()
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    room = repository.get_room("org-1", "room-1")

    assert room is not None
    assert room.id == "room-1"
    assert room.name == "General"
    mock_client.collection.return_value.document.assert_called_with("org-1")
    rooms.document.assert_called_once_with("room-1")


def test_get_room_returns_none_when_document_missing(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = False
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    room = repository.get_room("org-1", "room-missing")

    assert room is None


def test_list_rooms_for_user_queries_member_ids(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.id = "room-1"
    doc.to_dict.return_value = ROOM_DATA.copy()
    rooms = _rooms_collection(mock_client)
    rooms.where.return_value.stream.return_value = [doc]

    result = repository.list_rooms_for_user("org-1", "user-1")

    assert len(result) == 1
    assert result[0].id == "room-1"
    rooms.where.assert_called_once()


def test_create_room_writes_to_organization_scoped_collection(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc_ref = MagicMock()
    doc_ref.id = "room-new"
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value = doc_ref

    room = repository.create_room(
        "org-1",
        name="General",
        description="Team chat",
        member_ids=["user-1"],
        created_by="user-1",
        created_at=CREATED_AT,
    )

    assert room.id == "room-new"
    assert room.member_ids == ["user-1"]
    doc_ref.set.assert_called_once()


def test_add_member_updates_member_ids(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "room-1"
    doc.to_dict.return_value = ROOM_DATA.copy()
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    room = repository.add_member("org-1", "room-1", "user-3")

    assert room.member_ids == ["user-1", "user-2", "user-3"]
    rooms.document.return_value.update.assert_called_once_with(
        {"memberIds": ["user-1", "user-2", "user-3"]}
    )


def test_add_member_is_idempotent(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "room-1"
    doc.to_dict.return_value = ROOM_DATA.copy()
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    room = repository.add_member("org-1", "room-1", "user-1")

    assert room.member_ids == ["user-1", "user-2"]
    rooms.document.return_value.update.assert_not_called()


def test_remove_member_updates_member_ids(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "room-1"
    doc.to_dict.return_value = ROOM_DATA.copy()
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    room = repository.remove_member("org-1", "room-1", "user-2")

    assert room.member_ids == ["user-1"]
    rooms.document.return_value.update.assert_called_once_with({"memberIds": ["user-1"]})


def test_remove_member_raises_when_room_missing(
    repository: RoomRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = False
    rooms = _rooms_collection(mock_client)
    rooms.document.return_value.get.return_value = doc

    with pytest.raises(RoomNotFoundError):
        repository.remove_member("org-1", "room-missing", "user-2")
