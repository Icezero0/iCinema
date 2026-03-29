from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.realtime.constants import PlaybackStatusType, VideoSourceType

class PresenceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    present_user_ids: list[int]


class VideoSourceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    source_type: VideoSourceType
    external_url: str | None = None
    file_hash: str | None = None


class PlaybackState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    status: PlaybackStatusType
    position_seconds: float
    anchor_ts_ms: int
    playback_rate: float = 1.0


class RoomSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: int
    present_user_ids: list[int]
    video_source: VideoSourceState | None = None
    playback: PlaybackState | None = None