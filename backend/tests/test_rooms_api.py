from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_service
from app.dependencies.services import get_message_repository, get_room_authorization_service
from app.main import app
from app.models.auth import CurrentUser
from app.models.domain import Message, Room
from app.repositories.room_repository import RoomNotFoundError
from app.services.auth_service import AuthService
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ORG_A_MEMBER = CurrentUser(
    id="user-a",
    firebase_uid="firebase-a",
    name="Org A Member",
    email="a@example.com",
    organization_id="org-a",
    role="member",
)

ORG_A_ADMIN = CurrentUser(
    id="admin-a",
    firebase_uid="firebase-admin-a",
    name="Org A Admin",
    email="admin@example.com",
    organization_id="org-a",
    role="admin",
)

ORG_B_MEMBER = CurrentUser(
    id="user-b",
    firebase_uid="firebase-b",
    name="Org B Member",
    email="b@example.com",
    organization_id="org-b",
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
    content="Hello",
    created_at=CREATED_AT,
    status="complete",
)


@pytest.fixture
def mock_auth_service() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_room_authorization_service() -> MagicMock:
    return MagicMock(spec=RoomAuthorizationService)


@pytest.fixture
def mock_message_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_repository: MagicMock,
) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_room_authorization_service] = lambda: mock_room_authorization_service
    app.dependency_overrides[get_message_repository] = lambda: mock_message_repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


CREATE_ROOM_PAYLOAD = {
    "name": "General",
    "description": "Team chat",
    "memberIds": ["user-a"],
}


def test_create_room_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/rooms", json=CREATE_ROOM_PAYLOAD)
    assert response.status_code == 401


def test_create_room_denies_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.create_room.side_effect = RoomAccessDeniedError(
        "Admin role is required for this action"
    )

    response = client.post("/api/rooms", json=CREATE_ROOM_PAYLOAD, headers=auth_header())

    assert response.status_code == 403
    mock_room_authorization_service.create_room.assert_called_once()


def test_create_room_allows_admin(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    created_room = Room(
        id="room-new",
        name="General",
        description="Team chat",
        member_ids=["admin-a", "user-a"],
        created_by="admin-a",
        created_at=CREATED_AT,
    )
    mock_auth_service.authenticate.return_value = ORG_A_ADMIN
    mock_room_authorization_service.create_room.return_value = created_room

    response = client.post("/api/rooms", json=CREATE_ROOM_PAYLOAD, headers=auth_header())

    assert response.status_code == 201
    assert response.json() == {
        "id": "room-new",
        "name": "General",
        "description": "Team chat",
        "memberIds": ["admin-a", "user-a"],
        "createdBy": "admin-a",
        "createdAt": CREATED_AT.isoformat().replace("+00:00", "Z"),
    }
    mock_room_authorization_service.create_room.assert_called_once_with(
        ORG_A_ADMIN,
        name="General",
        description="Team chat",
        member_ids=["user-a"],
    )


def test_create_room_denies_cross_organization_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_ADMIN
    mock_room_authorization_service.create_room.side_effect = RoomAccessDeniedError(
        "User is not part of this organization"
    )

    response = client.post(
        "/api/rooms",
        json={
            "name": "General",
            "description": "Team chat",
            "memberIds": ["user-b"],
        },
        headers=auth_header(),
    )

    assert response.status_code == 403
    mock_room_authorization_service.create_room.assert_called_once()


def test_list_rooms_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/rooms")
    assert response.status_code == 401


def test_list_rooms_returns_member_rooms(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.list_rooms_for_user.return_value = [SAMPLE_ROOM]

    response = client.get("/api/rooms", headers=auth_header())

    assert response.status_code == 200
    assert response.json() == {
        "rooms": [
            {
                "id": "room-1",
                "name": "General",
                "description": "Team chat",
                "createdAt": CREATED_AT.isoformat().replace("+00:00", "Z"),
            }
        ]
    }


def test_list_room_messages_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/rooms/room-1/messages")
    assert response.status_code == 401


def test_list_room_messages_returns_messages_for_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.return_value = SAMPLE_ROOM
    mock_message_repository.get_messages.return_value = [SAMPLE_MESSAGE]

    response = client.get("/api/rooms/room-1/messages", headers=auth_header())

    assert response.status_code == 200
    assert response.json()["messages"][0]["id"] == "message-1"
    assert response.json()["messages"][0]["senderName"] == "Org A Member"
    mock_message_repository.get_messages.assert_called_once_with("org-a", "room-1", limit=50)


def test_list_room_messages_denies_non_member(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.side_effect = RoomAccessDeniedError(
        "Room membership is required for this action"
    )

    response = client.get("/api/rooms/room-1/messages", headers=auth_header())

    assert response.status_code == 403
    mock_message_repository.get_messages.assert_not_called()


def test_list_room_messages_denies_cross_organization_access(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_A_MEMBER
    mock_room_authorization_service.get_room_for_user.side_effect = RoomNotFoundError(
        "Room 'room-b1' was not found"
    )

    response = client.get("/api/rooms/room-b1/messages", headers=auth_header())

    assert response.status_code == 404
    mock_message_repository.get_messages.assert_not_called()


def test_organization_b_user_cannot_access_organization_a_messages(
    client: TestClient,
    mock_auth_service: MagicMock,
    mock_room_authorization_service: MagicMock,
    mock_message_repository: MagicMock,
) -> None:
    mock_auth_service.authenticate.return_value = ORG_B_MEMBER
    mock_room_authorization_service.get_room_for_user.side_effect = RoomNotFoundError(
        "Room 'room-a1' was not found"
    )

    response = client.get("/api/rooms/room-a1/messages", headers=auth_header())

    assert response.status_code == 404
    mock_room_authorization_service.get_room_for_user.assert_called_once()
    called_user, called_room_id = mock_room_authorization_service.get_room_for_user.call_args.args
    assert called_user.organization_id == "org-b"
    assert called_room_id == "room-a1"
    mock_message_repository.get_messages.assert_not_called()
