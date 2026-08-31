from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CurrentUser(BaseModel):
    id: str
    firebase_uid: str = Field(serialization_alias="firebaseUid")
    name: str
    email: str
    organization_id: str = Field(serialization_alias="organizationId")
    role: Literal["admin", "member"]

    model_config = ConfigDict(populate_by_name=True)


class UserSummary(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["admin", "member"]


class OrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str


class MeResponse(BaseModel):
    user: UserSummary
    organization: OrganizationSummary
