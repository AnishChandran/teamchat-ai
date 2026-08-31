from datetime import datetime, timezone

from app.models.auth import CurrentUser
from app.models.domain import Room
from app.repositories.room_repository import RoomNotFoundError, RoomRepository
from app.repositories.user_repository import UserRepository


class RoomAccessDeniedError(Exception):
    """Raised when the user is not allowed to access or modify a room."""


class RoomAuthorizationService:
    def __init__(
        self,
        room_repository: RoomRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._room_repository = room_repository or RoomRepository()
        self._user_repository = user_repository or UserRepository()

    def get_room_for_user(self, current_user: CurrentUser, room_id: str) -> Room:
        room = self._get_room_in_organization(current_user, room_id)
        self._require_member(current_user, room)
        return room

    def list_rooms_for_user(self, current_user: CurrentUser) -> list[Room]:
        return self._room_repository.list_rooms_for_user(
            current_user.organization_id,
            current_user.id,
        )

    def create_room(
        self,
        current_user: CurrentUser,
        name: str,
        description: str,
        member_ids: list[str] | None = None,
    ) -> Room:
        self._require_admin(current_user)

        resolved_member_ids = list(member_ids or [current_user.id])
        if current_user.id not in resolved_member_ids:
            resolved_member_ids.append(current_user.id)

        for member_id in resolved_member_ids:
            self._require_user_in_organization(current_user.organization_id, member_id)

        return self._room_repository.create_room(
            current_user.organization_id,
            name=name,
            description=description,
            member_ids=resolved_member_ids,
            created_by=current_user.id,
            created_at=datetime.now(timezone.utc),
        )

    def add_member(self, current_user: CurrentUser, room_id: str, user_id: str) -> Room:
        self._require_admin(current_user)
        self._get_room_in_organization(current_user, room_id)
        self._require_user_in_organization(current_user.organization_id, user_id)
        return self._room_repository.add_member(
            current_user.organization_id,
            room_id,
            user_id,
        )

    def remove_member(self, current_user: CurrentUser, room_id: str, user_id: str) -> Room:
        self._require_admin(current_user)
        self._get_room_in_organization(current_user, room_id)
        return self._room_repository.remove_member(
            current_user.organization_id,
            room_id,
            user_id,
        )

    def _get_room_in_organization(self, current_user: CurrentUser, room_id: str) -> Room:
        room = self._room_repository.get_room(current_user.organization_id, room_id)
        if room is None:
            raise RoomNotFoundError(f"Room '{room_id}' was not found")
        return room

    @staticmethod
    def _require_admin(current_user: CurrentUser) -> None:
        if current_user.role != "admin":
            raise RoomAccessDeniedError("Admin role is required for this action")

    @staticmethod
    def _require_member(current_user: CurrentUser, room: Room) -> None:
        if current_user.id not in room.member_ids:
            raise RoomAccessDeniedError("Room membership is required for this action")

    def _require_user_in_organization(self, organization_id: str, user_id: str) -> None:
        user = self._user_repository.get_user_by_id(organization_id, user_id)
        if user is None:
            raise RoomAccessDeniedError("User is not part of this organization")
