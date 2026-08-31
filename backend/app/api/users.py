from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_user_repository
from app.models.auth import CurrentUser, UserSummary
from app.models.responses import UsersResponse
from app.repositories.user_repository import UserRepository

router = APIRouter()


@router.get("/users", response_model=UsersResponse)
def list_users(
    current_user: CurrentUser = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UsersResponse:
    users = user_repository.list_users_for_organization(current_user.organization_id)
    return UsersResponse(
        users=[
            UserSummary(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
            )
            for user in users
        ],
    )
