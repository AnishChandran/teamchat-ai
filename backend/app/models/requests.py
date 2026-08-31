from pydantic import BaseModel, ConfigDict, Field


class CreateRoomRequest(BaseModel):
    name: str
    description: str
    member_ids: list[str] = Field(default_factory=list, alias="memberIds")

    model_config = ConfigDict(populate_by_name=True)
