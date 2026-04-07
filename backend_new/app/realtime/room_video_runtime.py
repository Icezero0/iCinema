from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import time

from app.core.exceptions import BadRequestError
from app.modules.rooms.constants import RoomSyncPolicy, RoomVideoSourceType
from app.realtime.constants import (
    AutoPlaybackAction,
    PlaybackStatusType,
    UserPlayerStatusType,
)
from app.realtime.state import (
    PlaybackState,
    RoomUserPlayerState,
    RoomVideoSourceState,
    UserPlayerStatesState,
)


def now_ms() -> int:
    return int(time() * 1000)


@dataclass
class UserPlayerStatesUpdateResult:
    user_player_states: UserPlayerStatesState
    auto_playback: PlaybackState | None = None
    auto_action: AutoPlaybackAction | None = None


@dataclass
class RoomVideoRuntimeState:
    room_id: int
    room_video_source: RoomVideoSourceState | None = None
    playback: PlaybackState | None = None
    user_player_states: dict[int, RoomUserPlayerState] = field(default_factory=dict)
    stalling_user_ids: set[int] = field(default_factory=set)
    paused_by_stall: bool = False


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
    def _copy_room_video_source(
        room_video_source: RoomVideoSourceState | None,
    ) -> RoomVideoSourceState | None:
        if room_video_source is None:
            return None
        return room_video_source.model_copy(deep=True)

    @staticmethod
    def _copy_playback(
        playback: PlaybackState | None,
    ) -> PlaybackState | None:
        if playback is None:
            return None
        return playback.model_copy(deep=True)

    @staticmethod
    def _copy_user_player_states(
        payload: UserPlayerStatesState,
    ) -> UserPlayerStatesState:
        return payload.model_copy(deep=True)

    @staticmethod
    def _require_room_video_source_set_locked(
        state: RoomVideoRuntimeState,
    ) -> None:
        if state.room_video_source is None:
            raise BadRequestError("Room video source is not set for this room")

    @staticmethod
    def _resolve_position_seconds_locked(
        playback: PlaybackState,
        *,
        at_ts_ms: int,
    ) -> float:
        if playback.status != PlaybackStatusType.PLAYING:
            return playback.position_seconds

        elapsed_ms = max(0, at_ts_ms - playback.anchor_ts_ms)
        return playback.position_seconds + (elapsed_ms / 1000.0) * playback.playback_rate

    @staticmethod
    def _build_user_player_states_locked(
        state: RoomVideoRuntimeState,
    ) -> UserPlayerStatesState:
        return UserPlayerStatesState(
            room_id=state.room_id,
            user_player_states=[
                user_player_state.model_copy(deep=True)
                for _, user_player_state in sorted(state.user_player_states.items())
            ],
        )

    async def get_room_video_source(
        self,
        *,
        room_id: int,
    ) -> RoomVideoSourceState | None:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return None
            return self._copy_room_video_source(state.room_video_source)

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

    async def get_user_player_states(
        self,
        *,
        room_id: int,
    ) -> UserPlayerStatesState:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return UserPlayerStatesState(room_id=room_id, user_player_states=[])
            return self._copy_user_player_states(self._build_user_player_states_locked(state))

    async def set_room_video_source(
        self,
        *,
        room_id: int,
        source_type: RoomVideoSourceType,
        external_url: str | None = None,
        file_hash: str | None = None,
        anchor_ts_ms: int | None = None,
    ) -> tuple[RoomVideoSourceState, PlaybackState, UserPlayerStatesState]:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)

            room_video_source = RoomVideoSourceState(
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

            state.room_video_source = room_video_source
            state.playback = playback
            state.user_player_states.clear()
            state.stalling_user_ids.clear()
            state.paused_by_stall = False

            return (
                self._copy_room_video_source(room_video_source),
                self._copy_playback(playback),
                self._copy_user_player_states(self._build_user_player_states_locked(state)),
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
            self._require_room_video_source_set_locked(state)

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PLAYING,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            state.paused_by_stall = False
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
            self._require_room_video_source_set_locked(state)

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PAUSED,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            state.paused_by_stall = False
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
            self._require_room_video_source_set_locked(state)

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
            state.paused_by_stall = False
            return self._copy_playback(playback)

    async def report_user_player_status(
        self,
        *,
        room_id: int,
        user_id: int,
        status: UserPlayerStatusType,
        reported_at_ms: int,
        sync_policy: RoomSyncPolicy,
        position_seconds: float | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> UserPlayerStatesUpdateResult:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            previous_state = state.user_player_states.get(user_id)
            previous_status = previous_state.status if previous_state is not None else None

            user_player_state = RoomUserPlayerState(
                room_id=room_id,
                user_id=user_id,
                status=status,
                reported_at_ms=reported_at_ms,
                position_seconds=position_seconds,
                error_code=error_code,
                error_message=error_message,
            )
            state.user_player_states[user_id] = user_player_state

            if status == UserPlayerStatusType.STALLING:
                state.stalling_user_ids.add(user_id)
            else:
                state.stalling_user_ids.discard(user_id)

            auto_playback: PlaybackState | None = None
            auto_action: AutoPlaybackAction | None = None

            if sync_policy == RoomSyncPolicy.AUTO_PAUSE:
                entered_stalling = (
                    status == UserPlayerStatusType.STALLING
                    and previous_status != UserPlayerStatusType.STALLING
                )
                left_stalling = (
                    previous_status == UserPlayerStatusType.STALLING
                    and status != UserPlayerStatusType.STALLING
                )

                if (
                    entered_stalling
                    and state.playback is not None
                    and state.playback.status == PlaybackStatusType.PLAYING
                    and not state.paused_by_stall
                ):
                    anchor_ts_ms = now_ms()
                    auto_playback = PlaybackState(
                        room_id=room_id,
                        status=PlaybackStatusType.PAUSED,
                        position_seconds=self._resolve_position_seconds_locked(
                            state.playback,
                            at_ts_ms=anchor_ts_ms,
                        ),
                        anchor_ts_ms=anchor_ts_ms,
                        playback_rate=state.playback.playback_rate,
                    )
                    state.playback = auto_playback
                    state.paused_by_stall = True
                    auto_action = AutoPlaybackAction.PAUSE
                elif left_stalling and not state.stalling_user_ids and state.paused_by_stall:
                    if state.playback is not None:
                        anchor_ts_ms = now_ms()
                        auto_playback = PlaybackState(
                            room_id=room_id,
                            status=PlaybackStatusType.PLAYING,
                            position_seconds=state.playback.position_seconds,
                            anchor_ts_ms=anchor_ts_ms,
                            playback_rate=state.playback.playback_rate,
                        )
                        state.playback = auto_playback
                        auto_action = AutoPlaybackAction.PLAY
                    state.paused_by_stall = False

            payload = self._build_user_player_states_locked(state)
            return UserPlayerStatesUpdateResult(
                user_player_states=self._copy_user_player_states(payload),
                auto_playback=self._copy_playback(auto_playback),
                auto_action=auto_action,
            )

    async def remove_user_player_state(
        self,
        *,
        room_id: int,
        user_id: int,
        sync_policy: RoomSyncPolicy,
    ) -> UserPlayerStatesUpdateResult | None:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return None

            previous_state = state.user_player_states.pop(user_id, None)
            if previous_state is None:
                return None

            if previous_state.status == UserPlayerStatusType.STALLING:
                state.stalling_user_ids.discard(user_id)

            auto_playback: PlaybackState | None = None
            auto_action: AutoPlaybackAction | None = None

            if (
                sync_policy == RoomSyncPolicy.AUTO_PAUSE
                and previous_state.status == UserPlayerStatusType.STALLING
                and not state.stalling_user_ids
                and state.paused_by_stall
            ):
                if state.playback is not None:
                    anchor_ts_ms = now_ms()
                    auto_playback = PlaybackState(
                        room_id=room_id,
                        status=PlaybackStatusType.PLAYING,
                        position_seconds=state.playback.position_seconds,
                        anchor_ts_ms=anchor_ts_ms,
                        playback_rate=state.playback.playback_rate,
                    )
                    state.playback = auto_playback
                    auto_action = AutoPlaybackAction.PLAY
                state.paused_by_stall = False

            payload = self._build_user_player_states_locked(state)
            return UserPlayerStatesUpdateResult(
                user_player_states=self._copy_user_player_states(payload),
                auto_playback=self._copy_playback(auto_playback),
                auto_action=auto_action,
            )

    async def clear_room_runtime(
        self,
        *,
        room_id: int,
    ) -> None:
        async with self._lock:
            self._room_states.pop(room_id, None)
