from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import get_firebase_project_id
from app.exceptions import ServiceUnavailableError
from app.models.auth import CurrentUser
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository


class AuthenticationError(Exception):
    """Raised when the Firebase ID token is missing or invalid."""


class AuthorizationError(Exception):
    """Raised when the token is valid but the user is not authorized in the app."""


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        organization_repository: OrganizationRepository | None = None,
    ) -> None:
        self._user_repository = user_repository or UserRepository()
        self._organization_repository = organization_repository or OrganizationRepository()

    def verify_id_token(self, token: str) -> dict:
        project_id = get_firebase_project_id()
        if not project_id:
            raise AuthenticationError("Server Firebase project is not configured")

        try:
            decoded = google_id_token.verify_firebase_token(
                token,
                google_requests.Request(),
                audience=project_id,
            )
        except ValueError as exc:
            raise AuthenticationError("Invalid authentication token") from exc

        claims = dict(decoded)
        if "uid" not in claims and "sub" in claims:
            claims["uid"] = claims["sub"]
        return claims

    def resolve_current_user(self, decoded_token: dict) -> CurrentUser:
        firebase_uid = decoded_token["uid"]
        organization_id = decoded_token.get("organizationId")
        if not organization_id:
            raise AuthorizationError("User is not registered in the application")

        try:
            user = self._user_repository.get_user_by_firebase_uid(organization_id, firebase_uid)
        except Exception as exc:
            raise ServiceUnavailableError(
                "Unable to verify account. Please try again.",
            ) from exc

        if user is None:
            raise AuthorizationError("User is not registered in the application")

        return CurrentUser(
            id=user.id,
            firebase_uid=user.firebase_uid,
            name=user.name,
            email=user.email,
            organization_id=organization_id,
            role=user.role,
        )

    def authenticate(self, token: str) -> CurrentUser:
        decoded_token = self.verify_id_token(token)
        return self.resolve_current_user(decoded_token)
