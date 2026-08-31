from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.domain import Organization
from app.repositories.organization_repository import OrganizationRepository

CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repository(mock_client: MagicMock) -> OrganizationRepository:
    return OrganizationRepository(client=mock_client)


def test_get_organization_returns_organization_when_document_exists(
    repository: OrganizationRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = True
    doc.id = "org-1"
    doc.to_dict.return_value = {
        "name": "Acme Corp",
        "slug": "acme-corp",
        "createdAt": CREATED_AT,
    }
    mock_client.collection.return_value.document.return_value.get.return_value = doc

    organization = repository.get_organization("org-1")

    assert organization is not None
    assert organization.id == "org-1"
    assert organization.name == "Acme Corp"
    assert organization.slug == "acme-corp"
    mock_client.collection.assert_called_once_with("organizations")
    mock_client.collection.return_value.document.assert_called_once_with("org-1")


def test_get_organization_returns_none_when_document_missing(
    repository: OrganizationRepository,
    mock_client: MagicMock,
) -> None:
    doc = MagicMock()
    doc.exists = False
    mock_client.collection.return_value.document.return_value.get.return_value = doc

    organization = repository.get_organization("org-missing")

    assert organization is None
