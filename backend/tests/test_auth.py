from app.services.auth_service import AuthenticationError, AuthorizationError

from tests.conftest import SAMPLE_CURRENT_USER, SAMPLE_ORGANIZATION, auth_header


def test_me_without_auth_header(client) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authentication credentials"


def test_me_with_malformed_authorization_header(client) -> None:
    response = client.get("/api/me", headers={"Authorization": "Token valid-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authentication credentials"


def test_me_with_invalid_token(client, mock_auth_service) -> None:
    mock_auth_service.authenticate.side_effect = AuthenticationError("Invalid authentication token")

    response = client.get("/api/me", headers=auth_header("bad-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"
    mock_auth_service.authenticate.assert_called_once_with("bad-token")


def test_me_with_valid_token_but_unregistered_user(client, mock_auth_service) -> None:
    mock_auth_service.authenticate.side_effect = AuthorizationError(
        "User is not registered in the application"
    )

    response = client.get("/api/me", headers=auth_header())

    assert response.status_code == 403
    assert response.json()["detail"] == "User is not registered in the application"


def test_me_with_valid_token_but_missing_organization(
    client,
    mock_auth_service,
    mock_organization_repository,
) -> None:
    mock_auth_service.authenticate.return_value = SAMPLE_CURRENT_USER
    mock_organization_repository.get_organization.return_value = None

    response = client.get("/api/me", headers=auth_header())

    assert response.status_code == 403
    assert response.json()["detail"] == "Organization is not accessible"
    mock_organization_repository.get_organization.assert_called_once_with("org-1")


def test_me_success(client, mock_auth_service, mock_organization_repository) -> None:
    mock_auth_service.authenticate.return_value = SAMPLE_CURRENT_USER
    mock_organization_repository.get_organization.return_value = SAMPLE_ORGANIZATION

    response = client.get("/api/me", headers=auth_header())

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": "user-1",
            "name": "Sarah Chen",
            "email": "sarah@example.com",
            "role": "admin",
        },
        "organization": {
            "id": "org-1",
            "name": "Acme Corp",
            "slug": "acme-corp",
        },
    }


def test_health_check_does_not_require_auth() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as unauthenticated_client:
        response = unauthenticated_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
