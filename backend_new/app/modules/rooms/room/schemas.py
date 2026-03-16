from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import normalize_optional_non_empty_str, normalize_required_str


class RoomCreate(BaseModel):
    name: str
    is_public: bool | None = True
    config: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Room name")


class RoomPatch(BaseModel):
    name: str | None = None
    is_public: bool | None = None
    config: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Room name")


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    is_public: bool | None
    config: str | None


class RoomListResponse(BaseModel):
    items: list[RoomResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
