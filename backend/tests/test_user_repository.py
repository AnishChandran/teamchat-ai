from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.domain import User
from app.repositories.user_repository import UserRepository

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

USER_DATA = {
    "firebaseUid": "firebase-uid-1",
    "name": "Sarah Chen",
    "email": "sarah@example.com",
    "role": "admin",
    "createdAt": CREATED_AT,
}


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repository(mock_client: MagicMock) -> UserRepository:
    return UserRepository(client=mock_client)


def _users_collection(mock_client: MagicMock) -> MagicMock:
    return (
        mock_client.collection.return_value.document.return_value.collection.return_value
    )


def test_get_user_by_firebase_uid_returns_user_when_found(
    repository: UserRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.id = "user-1"
    doc.to_dict.return_value = USER_DATA.copy()
    users = _users_collection(mock_client)
    users.where.return_value.limit.return_value.stream.return_value = [doc]

    user = repository.get_user_by_firebase_uid("org-1", "firebase-uid-1")

    assert user is not None
    assert user.id == "user-1"
    assert user.firebase_uid == "firebase-uid-1"
    mock_client.collection.assert_called_with("organizations")
    mock_client.collection.return_value.document.assert_called_with("org-1")
    users.where.assert_called_once()


def test_get_user_by_firebase_uid_returns_none_when_not_found(
    repository: UserRepository,
    mock_client: MagicMock,
) -> None:
    users = _users_collection(mock_client)
    users.where.return_value.limit.return_value.stream.return_value = []

    user = repository.get_user_by_firebase_uid("org-1", "missing-uid")

    assert user is None


def test_get_user_by_id_returns_user_when_document_exists(
    repository: UserRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "user-1"
    doc.to_dict.return_value = USER_DATA.copy()
    users = _users_collection(mock_client)
    users.document.return_value.get.return_value = doc

    user = repository.get_user_by_id("org-1", "user-1")

    assert user is not None
    assert user.id == "user-1"
    users.document.assert_called_once_with("user-1")


def test_get_user_by_id_returns_none_when_document_missing(
    repository: UserRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = False
    users = _users_collection(mock_client)
    users.document.return_value.get.return_value = doc

    user = repository.get_user_by_id("org-1", "user-missing")

    assert user is None


def test_list_users_for_organization_returns_all_users(
    repository: UserRepository,
    mock_client: MagicMock,
) -> None:
    doc_one = MagicMock()
    doc_one.id = "user-1"
    doc_one.to_dict.return_value = USER_DATA.copy()

    doc_two = MagicMock()
    doc_two.id = "user-2"
    doc_two.to_dict.return_value = {
        **USER_DATA,
        "firebaseUid": "firebase-uid-2",
        "name": "Mike Ross",
        "email": "mike@example.com",
        "role": "member",
    }

    users = _users_collection(mock_client)
    users.stream.return_value = [doc_one, doc_two]

    result = repository.list_users_for_organization("org-1")

    assert len(result) == 2
    assert result[0].id == "user-1"
    assert result[1].id == "user-2"
    assert all(isinstance(user, User) for user in result)
    mock_client.collection.return_value.document.assert_called_with("org-1")
