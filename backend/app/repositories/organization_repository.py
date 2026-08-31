from google.cloud import firestore

from app.core.firestore import get_firestore_client
from app.models.domain import Organization
from app.repositories.firestore_utils import organization_document, serialize_document


class OrganizationRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> firestore.Client:
        if self._client is None:
            return get_firestore_client()
        return self._client

    def get_organization(self, organization_id: str) -> Organization | None:
        doc = organization_document(self.client, organization_id).get()
        if not doc.exists:
            return None

        data = serialize_document(doc)
        return Organization.model_validate({"id": doc.id, **data})
