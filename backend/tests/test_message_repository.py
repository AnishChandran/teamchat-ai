from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.domain import Message
from app.repositories.message_repository import MessageRepository

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

MESSAGE_DATA = {
    "senderId": "user-1",
    "senderName": "Sarah Chen",
    "type": "user",
    "content": "Hello team",
    "status": "complete",
    "createdAt": CREATED_AT,
}


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repository(mock_client: MagicMock) -> MessageRepository:
    return MessageRepository(client=mock_client)


def _messages_collection(mock_client: MagicMock) -> MagicMock:
    return (
        mock_client.collection.return_value.document.return_value.collection.return_value
        .document.return_value.collection.return_value
    )


def test_get_messages_queries_room_scoped_collection_ordered_by_created_at(
    repository: MessageRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.id = "message-1"
    doc.to_dict.return_value = MESSAGE_DATA.copy()
    messages = _messages_collection(mock_client)
    messages.order_by.return_value.limit.return_value.stream.return_value = [doc]

    result = repository.get_messages("org-1", "room-1", limit=50)

    assert len(result) == 1
    assert result[0].id == "message-1"
    assert result[0].sender_name == "Sarah Chen"
    mock_client.collection.assert_called_with("organizations")
    mock_client.collection.return_value.document.assert_called_with("org-1")
    messages.order_by.assert_called_once()
    messages.order_by.return_value.limit.assert_called_once_with(50)


def test_get_message_returns_message_when_document_exists(
    repository: MessageRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "message-1"
    doc.to_dict.return_value = MESSAGE_DATA.copy()
    messages = _messages_collection(mock_client)
    messages.document.return_value.get.return_value = doc

    message = repository.get_message("org-1", "room-1", "message-1")

    assert message is not None
    assert message.id == "message-1"
    assert message.type == "user"
    assert message.status == "complete"


def test_get_message_returns_none_when_document_missing(
    repository: MessageRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = False
    messages = _messages_collection(mock_client)
    messages.document.return_value.get.return_value = doc

    message = repository.get_message("org-1", "room-1", "message-missing")

    assert message is None


def test_create_message_stores_sender_name_type_and_status(
    repository: MessageRepository,
    mock_client: MagicMock,
) -> None:
    doc_ref = MagicMock()
    doc_ref.id = "message-new"
    messages = _messages_collection(mock_client)
    messages.document.return_value = doc_ref

    message = repository.create_message(
        "org-1",
        "room-1",
        sender_id="user-1",
        sender_name="Sarah Chen",
        type="ai",
        content="Here is a response",
        status="streaming",
        created_at=CREATED_AT,
    )

    assert message.id == "message-new"
    assert message.sender_name == "Sarah Chen"
    assert message.type == "ai"
    assert message.status == "streaming"
    doc_ref.set.assert_called_once()
