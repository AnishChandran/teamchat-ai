from fastapi import APIRouter

from app.api.me import router as me_router
from app.api.rooms import router as rooms_router
from app.api.users import router as users_router

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


api_router = APIRouter(prefix="/api")
api_router.include_router(me_router)
api_router.include_router(rooms_router)
api_router.include_router(users_router)

public_router = APIRouter()
public_router.include_router(router)
public_router.include_router(api_router)
