from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.validators import normalize_optional_non_empty_str, normalize_required_str
from app.modules.rooms.constants import (
    RoomJoinAuditMode,
    RoomRole,
    RoomVisibility,
)
from app.modules.users.schemas import UserBriefResponse


class RoomCreate(BaseModel):
    name: str
    visibility: RoomVisibility = RoomVisibility.PRIVATE
    join_audit_mode: RoomJoinAuditMode = RoomJoinAuditMode.MANUAL_REVIEW

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Room name")


class RoomPatch(BaseModel):
    name: str | None = None
    visibility: RoomVisibility | None = None
    join_audit_mode: RoomJoinAuditMode | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Room name")


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    visibility: RoomVisibility
    join_audit_mode: RoomJoinAuditMode


class RoomListResponse(BaseModel):
    items: list[RoomResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class RoomBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    visibility: RoomVisibility


class UserRoomSummaryResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    owner: UserBriefResponse
    my_role: RoomRole
    visibility: RoomVisibility = Field(exclude=True)

    @computed_field
    @property
    def is_public(self) -> bool:
        return self.visibility == RoomVisibility.PUBLIC


class UserRoomSummaryListResponse(BaseModel):
    items: list[UserRoomSummaryResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
