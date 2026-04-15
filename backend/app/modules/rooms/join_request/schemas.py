from enum import StrEnum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.rooms.constants import (
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomJoinRequestAction,
)
from app.modules.rooms.room.schemas import RoomBriefResponse
from app.modules.users.schemas import UserBriefResponse


class RoomJoinRequestCreate(BaseModel):
    target_user_id: int


class RoomJoinRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    initiator_user_id: int
    target_user_id: int

    source: RoomJoinRequestSource
    status: RoomJoinRequestStatus

    room_action: RoomJoinRequestAction
    target_action: RoomJoinRequestAction

    room_action_by_user_id: int | None

    created_at: datetime | None
    updated_at: datetime | None

    room: RoomBriefResponse | None = None
    initiator: UserBriefResponse | None = None
    target: UserBriefResponse | None = None
    room_action_by: UserBriefResponse | None = None


class RoomJoinRequestListResponse(BaseModel):
    items: list[RoomJoinRequestResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class RoomJoinRequestListScope(StrEnum):
    PENDING_FOR_ME = "pending_for_me"
    CREATED_BY_ME = "created_by_me"
    ALL_RELATED_TO_ME = "all_related_to_me"


class RoomJoinRequestSortBy(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
