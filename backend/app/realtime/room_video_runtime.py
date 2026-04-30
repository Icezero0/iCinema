from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import time

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError
from app.modules.rooms.constants import RoomSyncPolicy, RoomVideoSourceType
from app.realtime.constants import (
    AutoPlaybackAction,
    PlaybackHoldReason,
    PlaybackStatusType,
    ResourceHealthStatusType,
)
from app.realtime.state import (
    PlaybackState,
    RoomUserResourceState,
    RoomVideoSourceState,
    UserResourceStatesState,
)


def now_ms() -> int:
    return int(time() * 1000)


@dataclass
class UserResourceStatesUpdateResult:
    user_resource_states: UserResourceStatesState
    auto_playback: PlaybackState | None = None
    auto_action: AutoPlaybackAction | None = None


@dataclass
class RoomSessionExitResult:
    room_cleared: bool
    user_resource_states: UserResourceStatesState | None = None
    auto_playback: PlaybackState | None = None
    auto_action: AutoPlaybackAction | None = None


@dataclass
class RoomVideoRuntimeState:
    room_id: int
    room_video_source: RoomVideoSourceState | None = None
    playback: PlaybackState | None = None
    user_resource_states: dict[int, RoomUserResourceState] = field(default_factory=dict)
    stalling_user_ids: set[int] = field(default_factory=set)
    playback_hold_reason: PlaybackHoldReason = PlaybackHoldReason.NONE


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
    def _copy_user_resource_states(
        payload: UserResourceStatesState,
    ) -> UserResourceStatesState:
        return payload.model_copy(deep=True)

    @staticmethod
    def _require_room_video_source_set_locked(
        state: RoomVideoRuntimeState,
    ) -> None:
        if state.room_video_source is None:
            raise BadRequestError(
                "Room video source is not set for this room",
                reason=ErrorReason.ROOM_VIDEO_SOURCE_NOT_SET,
                details={"room_id": state.room_id},
            )

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
    def _build_user_resource_states_locked(
        state: RoomVideoRuntimeState,
    ) -> UserResourceStatesState:
        return UserResourceStatesState(
            room_id=state.room_id,
            user_resource_states=[
                user_resource_state.model_copy(deep=True)
                for _, user_resource_state in sorted(state.user_resource_states.items())
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

    async def get_user_resource_states(
        self,
        *,
        room_id: int,
    ) -> UserResourceStatesState:
        async with self._lock:
            state = self._room_states.get(room_id)
            if state is None:
                return UserResourceStatesState(room_id=room_id, user_resource_states=[])
            return self._copy_user_resource_states(self._build_user_resource_states_locked(state))

    async def set_room_video_source(
        self,
        *,
        room_id: int,
        source_type: RoomVideoSourceType,
        external_url: str | None = None,
        file_hash: str | None = None,
        anchor_ts_ms: int | None = None,
    ) -> tuple[RoomVideoSourceState, PlaybackState, UserResourceStatesState]:
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
            state.user_resource_states.clear()
            state.stalling_user_ids.clear()
            state.playback_hold_reason = PlaybackHoldReason.NONE

            return (
                self._copy_room_video_source(room_video_source),
                self._copy_playback(playback),
                self._copy_user_resource_states(self._build_user_resource_states_locked(state)),
            )

    async def play(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
        sync_policy: RoomSyncPolicy,
        playback_rate: float = 1.0,
    ) -> PlaybackState:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            self._require_room_video_source_set_locked(state)

            if sync_policy == RoomSyncPolicy.AUTO_SYNC and state.stalling_user_ids:
                raise BadRequestError(
                    "Cannot resume playback while some users are still stalling",
                    reason=ErrorReason.PLAYBACK_RESUME_BLOCKED_BY_STALLING_USERS,
                    details={
                        "room_id": room_id,
                        "stalling_user_ids": sorted(state.stalling_user_ids),
                    },
                )

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PLAYING,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            state.playback_hold_reason = PlaybackHoldReason.NONE
            return self._copy_playback(playback)

    async def pause(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
        sync_policy: RoomSyncPolicy,
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
            state.playback_hold_reason = (
                PlaybackHoldReason.MANUAL
                if sync_policy == RoomSyncPolicy.AUTO_SYNC
                else PlaybackHoldReason.NONE
            )
            return self._copy_playback(playback)

    async def seek(
        self,
        *,
        room_id: int,
        position_seconds: float,
        anchor_ts_ms: int,
        sync_policy: RoomSyncPolicy,
    ) -> PlaybackState:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            self._require_room_video_source_set_locked(state)

            current = state.playback
            playback_rate = current.playback_rate if current is not None else 1.0

            playback = PlaybackState(
                room_id=room_id,
                status=PlaybackStatusType.PAUSED,
                position_seconds=position_seconds,
                anchor_ts_ms=anchor_ts_ms,
                playback_rate=playback_rate,
            )
            state.playback = playback
            state.playback_hold_reason = (
                PlaybackHoldReason.MANUAL
                if sync_policy == RoomSyncPolicy.AUTO_SYNC
                else PlaybackHoldReason.NONE
            )
            return self._copy_playback(playback)

    async def report_user_resource_status(
        self,
        *,
        room_id: int,
        user_id: int,
        status: ResourceHealthStatusType,
        reported_at_ms: int,
        sync_policy: RoomSyncPolicy,
        position_seconds: float | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> UserResourceStatesUpdateResult:
        async with self._lock:
            state = self._get_or_create_room_state_locked(room_id)
            previous_state = state.user_resource_states.get(user_id)
            previous_status = previous_state.status if previous_state is not None else None

            user_resource_state = RoomUserResourceState(
                room_id=room_id,
                user_id=user_id,
                status=status,
                reported_at_ms=reported_at_ms,
                position_seconds=position_seconds,
                error_code=error_code,
                error_message=error_message,
            )
            state.user_resource_states[user_id] = user_resource_state

            if status == ResourceHealthStatusType.STALLING:
                state.stalling_user_ids.add(user_id)
            else:
                state.stalling_user_ids.discard(user_id)

            auto_playback: PlaybackState | None = None
            auto_action: AutoPlaybackAction | None = None

            if sync_policy == RoomSyncPolicy.AUTO_SYNC:
                entered_stalling = (
                    status == ResourceHealthStatusType.STALLING
                    and previous_status != ResourceHealthStatusType.STALLING
                )
                left_stalling = (
                    previous_status == ResourceHealthStatusType.STALLING
                    and status != ResourceHealthStatusType.STALLING
                )

                if (
                    entered_stalling
                    and state.playback is not None
                    and state.playback.status == PlaybackStatusType.PLAYING
                    and state.playback_hold_reason != PlaybackHoldReason.STALL
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
                    state.playback_hold_reason = PlaybackHoldReason.STALL
                    auto_action = AutoPlaybackAction.PAUSE
                elif (
                    left_stalling
                    and not state.stalling_user_ids
                    and state.playback_hold_reason == PlaybackHoldReason.STALL
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
                    state.playback_hold_reason = PlaybackHoldReason.NONE

            payload = self._build_user_resource_states_locked(state)
            return UserResourceStatesUpdateResult(
                user_resource_states=self._copy_user_resource_states(payload),
                auto_playback=self._copy_playback(auto_playback),
                auto_action=auto_action,
            )

    async def handle_room_session_exit(
        self,
        *,
        room_id: int,
        user_id: int,
        sync_policy: RoomSyncPolicy,
        room_empty: bool,
    ) -> RoomSessionExitResult:
        async with self._lock:
            if room_empty:
                self._room_states.pop(room_id, None)
                return RoomSessionExitResult(room_cleared=True)

            state = self._room_states.get(room_id)
            if state is None:
                return RoomSessionExitResult(
                    room_cleared=False,
                    user_resource_states=UserResourceStatesState(
                        room_id=room_id,
                        user_resource_states=[],
                    ),
                )

            previous_state = state.user_resource_states.pop(user_id, None)
            if previous_state is None:
                return RoomSessionExitResult(
                    room_cleared=False,
                    user_resource_states=self._copy_user_resource_states(
                        self._build_user_resource_states_locked(state)
                    ),
                )

            if previous_state.status == ResourceHealthStatusType.STALLING:
                state.stalling_user_ids.discard(user_id)

            auto_playback: PlaybackState | None = None
            auto_action: AutoPlaybackAction | None = None

            if (
                sync_policy == RoomSyncPolicy.AUTO_SYNC
                and previous_state.status == ResourceHealthStatusType.STALLING
                and not state.stalling_user_ids
                and state.playback_hold_reason == PlaybackHoldReason.STALL
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
                state.playback_hold_reason = PlaybackHoldReason.NONE

            payload = self._build_user_resource_states_locked(state)
            return RoomSessionExitResult(
                room_cleared=False,
                user_resource_states=self._copy_user_resource_states(payload),
                auto_playback=self._copy_playback(auto_playback),
                auto_action=auto_action,
            )

    async def remove_user_resource_state(
        self,
        *,
        room_id: int,
        user_id: int,
        sync_policy: RoomSyncPolicy,
    ) -> UserResourceStatesUpdateResult | None:
        result = await self.handle_room_session_exit(
            room_id=room_id,
            user_id=user_id,
            sync_policy=sync_policy,
            room_empty=False,
        )
        if result.user_resource_states is None:
            return None
        return UserResourceStatesUpdateResult(
            user_resource_states=result.user_resource_states,
            auto_playback=result.auto_playback,
            auto_action=result.auto_action,
        )

    async def clear_room_runtime(
        self,
        *,
        room_id: int,
    ) -> None:
        async with self._lock:
            self._room_states.pop(room_id, None)
