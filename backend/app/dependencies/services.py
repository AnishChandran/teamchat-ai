from app.repositories.message_repository import MessageRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.room_authorization_service import RoomAuthorizationService


def get_room_authorization_service() -> RoomAuthorizationService:
    return RoomAuthorizationService()


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_organization_repository() -> OrganizationRepository:
    return OrganizationRepository()


def get_user_repository() -> UserRepository:
    return UserRepository()
