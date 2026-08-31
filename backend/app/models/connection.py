from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConnectionMetadata(BaseModel):
    connection_id: str = Field(serialization_alias="connectionId")
    user_id: str = Field(serialization_alias="userId")
    organization_id: str = Field(serialization_alias="organizationId")
    user_name: str = Field(serialization_alias="userName")
    connected_at: datetime = Field(serialization_alias="connectedAt")

    model_config = ConfigDict(populate_by_name=True)
