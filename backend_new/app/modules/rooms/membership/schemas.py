from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.rooms.constants import RoomRole
from app.modules.users.schemas import UserBriefResponse


class RoomMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    user_id: int
    joined_at: datetime | None
    role: RoomRole
    user: UserBriefResponse | None = None


class RoomMemberListResponse(BaseModel):
    items: list[RoomMemberResponse] = Field(default_factory=list)
    total: int
