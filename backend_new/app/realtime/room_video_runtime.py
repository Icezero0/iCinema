from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import time

from app.core.exceptions import BadRequestError
from app.realtime.constants import PlaybackStatusType, VideoSourceType
from app.realtime.state import PlaybackState, VideoSourceState


def now_ms() -> int:
    return int(time() * 1000)


@dataclass
class RoomVideoRuntimeState:
    room_id: int
    video_source: VideoSourceState | None = None
    playback: PlaybackState | None = None


class RoomVideoRuntimeService:
    def __init__(self) -> None:
        self._room_states: dict[int, RoomVideoRuntimeState] = {}
        self._lock = asyncio.Lock()

    def _get_or_create_room_state_locked(self, room_id: int) -> RoomVideoRuntimeState:
        state = self._room_states.get(room_id)
        if state is None:
            state = RoomVideoRuntimeState(room_id=room_id)
            self._room_states[room_id] = state
        return state

    @staticmethod
    def _copy_video_source(
        video_source: VideoSourceState | None,
    ) -> VideoSourceState | None:
        if video_source is None:
            return None
        return video_source.model_copy(deep=True)

    @staticmethod
    def _copy_playback(
        playback: PlaybackState | None,
    ) -> PlaybackState | None:
        if playback is None:
            return None
        return playback.model_copy(deep=True)

    @staticmethod
    def _require_source_set_locked(
        state: RoomVideoRuntimeState,
    ) -> None:
        if state.video_source is None:
            raise BadRequestError("Video source is not set for this room")

    async def get_video_source(
        self,
        *,
        room_id: int,
    ) -> VideoSourceState | None:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return None
            return self._copy_video_source(state.video_source)

    async def get_playback(
        self,
        *,
        room_id: int,
    ) -> PlaybackState | None:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return None
            return self._copy_playback(state.playback)

    async def set_video_source(
        self,
        *,
        room_id: int,
        source_type: VideoSourceType,
        external_url: str | None = None,
        file_hash: str | None = None,
        anchor_ts_ms: int | None = None,
    ) -> tuple[VideoSourceState, PlaybackState]:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)

            video_source = VideoSourceState(
                room_id=room_id,
                source_type=source_type,
                external_url=external_url,
                file_hash=file_hash,
            )
            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PAUSED,
                position_seconds=0.0,
                anchor_ts_ms=anchor_ts_ms or now_ms(),
                playback_rate=1.0,
            )

            state.video_source = video_source
            state.playback = playback

            return (
                self._copy_video_source(video_source),
                self._copy_playback(playback),
            )

    async def play(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
        playback_rate: float = 1.0,
    ) -> PlaybackState:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            self._require_source_set_locked(state)

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PLAYING,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            return self._copy_playback(playback)

    async def pause(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
        playback_rate: float = 1.0,
    ) -> PlaybackState:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            self._require_source_set_locked(state)

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PAUSED,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            return self._copy_playback(playback)

    async def seek(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
    ) -> PlaybackState:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            self._require_source_set_locked(state)

            current = state.playback
            status = current.status if current is not None else PlaybackStatusType.PAUSED
            playback_rate = current.playback_rate if current is not None else 1.0

            playback = PlaybackState(
                room_id=room_id,
                status=status,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            return self._copy_playback(playback)

    async def clear_room_runtime(
        self,
        *,
        room_id: int,
    ) -> None:
        async with self._lock:
            self._room_states.pop(room_id, None)