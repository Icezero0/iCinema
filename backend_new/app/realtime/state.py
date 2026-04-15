from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.rooms.constants import RoomVideoSourceType
from app.realtime.constants import PlaybackStatusType, UserPlayerStatusType


class PresenceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    present_user_ids: list[int]


class RoomVideoSourceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    source_type: RoomVideoSourceType
    external_url: str | None = None
    file_hash: str | None = None


class PlaybackState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    status: PlaybackStatusType
    position_seconds: float
    anchor_ts_ms: int
    playback_rate: float = 1.0


class RoomUserPlayerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    user_id: int
    status: UserPlayerStatusType
    reported_at_ms: int
    position_seconds: float | None = None
    error_code: str | None = None
    error_message: str | None = None


class UserPlayerStatesState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    user_player_states: list[RoomUserPlayerState]


class RoomSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    present_user_ids: list[int]
    room_video_source: RoomVideoSourceState | None = None
    playback: PlaybackState | None = None
    user_player_states: UserPlayerStatesState | None = None
