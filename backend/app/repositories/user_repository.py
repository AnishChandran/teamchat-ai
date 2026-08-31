from google.cloud import firestore

from app.core.firestore import get_firestore_client
from app.models.domain import User
from app.repositories.firestore_utils import serialize_document, users_collection


class UserRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> firestore.Client:
        if self._client is None:
            return get_firestore_client()
        return self._client

    def get_user_by_firebase_uid(
        self,
        organization_id: str,
        firebase_uid: str,
    ) -> User | None:
        query = (
            users_collection(self.client, organization_id)
            .where(filter=firestore.FieldFilter("firebaseUid", "==", firebase_uid))
            .limit(1)
        )
        docs = list(query.stream())
        if not docs:
            return None

        doc = docs[0]
        data = serialize_document(doc)
        return User.model_validate({"id": doc.id, **data})

    def get_user_by_id(self, organization_id: str, user_id: str) -> User | None:
        doc = users_collection(self.client, organization_id).document(user_id).get()
        if not doc.exists:
            return None

        data = serialize_document(doc)
        return User.model_validate({"id": doc.id, **data})

    def list_users_for_organization(self, organization_id: str) -> list[User]:
        docs = users_collection(self.client, organization_id).stream()
        users: list[User] = []
        for doc in docs:
            data = serialize_document(doc)
            users.append(User.model_validate({"id": doc.id, **data}))
        return users
