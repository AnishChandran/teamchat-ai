from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from app.dependencies.auth import get_auth_service
from app.exceptions import ServiceUnavailableError
from app.services.ai_chat_service import AiChatService
from app.services.auth_service import AuthenticationError, AuthService, AuthorizationError
from app.services.message_service import MessageService
from app.services.presence_service import PresenceService
from app.services.room_authorization_service import RoomAuthorizationService
from app.services.typing_service import TypingService
from app.websocket.connection_manager import ConnectionManager
from app.websocket.event_handler import WebSocketRoomEventHandler

router = APIRouter()


def get_ws_connection_manager(websocket: WebSocket) -> ConnectionManager:
    return websocket.app.state.connection_manager


def get_ws_room_authorization_service(websocket: WebSocket) -> RoomAuthorizationService:
    service = getattr(websocket.app.state, "room_authorization_service", None)
    if service is None:
        return RoomAuthorizationService()
    return service


def get_ws_message_service(websocket: WebSocket) -> MessageService:
    service = getattr(websocket.app.state, "message_service", None)
    if service is None:
        return MessageService(room_authorization_service=get_ws_room_authorization_service(websocket))
    return service


def get_ws_presence_service(websocket: WebSocket) -> PresenceService:
    service = getattr(websocket.app.state, "presence_service", None)
    if service is None:
        return PresenceService(get_ws_connection_manager(websocket))
    return service


def get_ws_typing_service(websocket: WebSocket) -> TypingService:
    service = getattr(websocket.app.state, "typing_service", None)
    if service is None:
        return TypingService(get_ws_connection_manager(websocket))
    return service


def get_ws_ai_chat_service(websocket: WebSocket) -> AiChatService:
    service = getattr(websocket.app.state, "ai_chat_service", None)
    if service is None:
        return AiChatService()
    return service


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    connection_manager = get_ws_connection_manager(websocket)
    presence_service = get_ws_presence_service(websocket)
    typing_service = get_ws_typing_service(websocket)
    ai_chat_service = get_ws_ai_chat_service(websocket)

    try:
        current_user = auth_service.authenticate(token)
    except (AuthenticationError, AuthorizationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except ServiceUnavailableError:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    await websocket.accept()
    metadata = connection_manager.register(websocket, current_user)
    event_handler = WebSocketRoomEventHandler(
        connection_id=metadata.connection_id,
        current_user=current_user,
        connection_manager=connection_manager,
        room_authorization_service=get_ws_room_authorization_service(websocket),
        message_service=get_ws_message_service(websocket),
        presence_service=presence_service,
        typing_service=typing_service,
        ai_chat_service=ai_chat_service,
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            await event_handler.handle_message(raw_message)
    except WebSocketDisconnect:
        pass
    finally:
        affected_rooms = connection_manager.unregister(metadata.connection_id)
        for organization_id, room_id in affected_rooms:
            await typing_service.clear_user_in_room_and_broadcast(
                organization_id,
                room_id,
                current_user.id,
            )
            await presence_service.broadcast_room_presence(organization_id, room_id)
