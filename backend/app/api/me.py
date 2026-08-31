from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_organization_repository
from app.models.auth import CurrentUser, MeResponse, OrganizationSummary, UserSummary
from app.repositories.organization_repository import OrganizationRepository

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> MeResponse:
    organization = organization_repository.get_organization(current_user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not accessible",
        )

    return MeResponse(
        user=UserSummary(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=current_user.role,
        ),
        organization=OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
        ),
    )
