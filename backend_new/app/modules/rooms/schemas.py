from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    name: str
    is_public: bool | None = True
    config: str | None = None


class RoomPatch(BaseModel):
    name: str | None = None
    is_public: bool | None = None
    config: str | None = None


class RoomMemberUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    email: str


class RoomMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    user_id: int
    joined_at: datetime | None
    role: str
    user: RoomMemberUserResponse | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    is_public: bool | None
    config: str | None
    created_at: datetime | None


class RoomListResponse(BaseModel):
    items: list[RoomResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int