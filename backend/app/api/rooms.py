from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_message_repository, get_room_authorization_service
from app.models.auth import CurrentUser
from app.models.domain import Room
from app.models.requests import CreateRoomRequest
from app.models.responses import MessagesResponse, RoomResponse, RoomSummary, RoomsResponse
from app.repositories.message_repository import MessageRepository
from app.repositories.room_repository import RoomNotFoundError
from app.services.room_authorization_service import RoomAccessDeniedError, RoomAuthorizationService

router = APIRouter(prefix="/rooms", tags=["rooms"])

MAX_MESSAGE_LIMIT = 100


def _room_to_summary(room: Room) -> RoomSummary:
    return RoomSummary(
        id=room.id,
        name=room.name,
        description=room.description,
        created_at=room.created_at,
    )


def _room_to_response(room: Room) -> RoomResponse:
    return RoomResponse(
        id=room.id,
        name=room.name,
        description=room.description,
        member_ids=room.member_ids,
        created_by=room.created_by,
        created_at=room.created_at,
    )


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: CreateRoomRequest,
    current_user: CurrentUser = Depends(get_current_user),
    room_authorization_service: RoomAuthorizationService = Depends(get_room_authorization_service),
) -> RoomResponse:
    try:
        room = room_authorization_service.create_room(
            current_user,
            name=payload.name,
            description=payload.description,
            member_ids=payload.member_ids,
        )
    except RoomAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return _room_to_response(room)


@router.get("", response_model=RoomsResponse)
def list_rooms(
    current_user: CurrentUser = Depends(get_current_user),
    room_authorization_service: RoomAuthorizationService = Depends(get_room_authorization_service),
) -> RoomsResponse:
    rooms = room_authorization_service.list_rooms_for_user(current_user)
    return RoomsResponse(rooms=[_room_to_summary(room) for room in rooms])


@router.get("/{room_id}/messages", response_model=MessagesResponse)
def list_room_messages(
    room_id: str,
    limit: int = Query(default=50, ge=1, le=MAX_MESSAGE_LIMIT),
    current_user: CurrentUser = Depends(get_current_user),
    room_authorization_service: RoomAuthorizationService = Depends(get_room_authorization_service),
    message_repository: MessageRepository = Depends(get_message_repository),
) -> MessagesResponse:
    try:
        room_authorization_service.get_room_for_user(current_user, room_id)
    except RoomNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        ) from exc
    except RoomAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Room membership is required for this action",
        ) from exc

    messages = message_repository.get_messages(
        current_user.organization_id,
        room_id,
        limit=limit,
    )
    return MessagesResponse(messages=messages)
