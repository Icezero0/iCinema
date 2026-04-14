import pytest

from app.core.exceptions import BadRequestError
from app.modules.rooms.constants import RoomSyncPolicy, RoomVideoSourceType
from app.realtime.constants import (
    AutoPlaybackAction,
    PlaybackStatusType,
    UserPlayerStatusType,
)
from app.realtime.room_video_runtime import RoomVideoRuntimeService


async def test_set_room_video_source_resets_playback_and_player_state() -> None:
    service = RoomVideoRuntimeService()

    room_video_source, playback, user_player_states = await service.set_room_video_source(
        room_id=101,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.m3u8",
        anchor_ts_ms=123456,
    )

    assert room_video_source.room_id == 101
    assert room_video_source.external_url == "https://example.com/video.m3u8"
    assert playback.status == PlaybackStatusType.PAUSED
    assert playback.position_seconds == 0.0
    assert playback.anchor_ts_ms == 123456
    assert user_player_states.user_player_states == []


async def test_auto_pause_and_resume_when_stalling_user_reports_status() -> None:
    service = RoomVideoRuntimeService()
    room_id = 202

    await service.set_room_video_source(
        room_id=room_id,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
    )
    await service.play(
        room_id=room_id,
        position_seconds=12.5,
        anchor_ts_ms=1000,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
        playback_rate=1.0,
    )

    stalling_result = await service.report_user_player_status(
        room_id=room_id,
        user_id=1,
        status=UserPlayerStatusType.STALLING,
        reported_at_ms=1100,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    assert stalling_result.auto_action == AutoPlaybackAction.PAUSE
    assert stalling_result.auto_playback is not None
    assert stalling_result.auto_playback.status == PlaybackStatusType.PAUSED

    recovered_result = await service.report_user_player_status(
        room_id=room_id,
        user_id=1,
        status=UserPlayerStatusType.READY,
        reported_at_ms=1200,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    assert recovered_result.auto_action == AutoPlaybackAction.PLAY
    assert recovered_result.auto_playback is not None
    assert recovered_result.auto_playback.status == PlaybackStatusType.PLAYING


async def test_manual_pause_blocks_auto_resume_in_auto_pause_mode() -> None:
    service = RoomVideoRuntimeService()
    room_id = 303

    await service.set_room_video_source(
        room_id=room_id,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
    )
    await service.play(
        room_id=room_id,
        position_seconds=5.0,
        anchor_ts_ms=1000,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    await service.pause(
        room_id=room_id,
        position_seconds=6.0,
        anchor_ts_ms=1100,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    await service.report_user_player_status(
        room_id=room_id,
        user_id=1,
        status=UserPlayerStatusType.STALLING,
        reported_at_ms=1200,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )
    recovered_result = await service.report_user_player_status(
        room_id=room_id,
        user_id=1,
        status=UserPlayerStatusType.READY,
        reported_at_ms=1300,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    assert recovered_result.auto_action is None
    playback = await service.get_playback(room_id=room_id)
    assert playback is not None
    assert playback.status == PlaybackStatusType.PAUSED


async def test_manual_seek_in_auto_pause_mode_pauses_until_manual_play() -> None:
    service = RoomVideoRuntimeService()
    room_id = 404

    await service.set_room_video_source(
        room_id=room_id,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
    )
    await service.play(
        room_id=room_id,
        position_seconds=8.0,
        anchor_ts_ms=1000,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    playback = await service.seek(
        room_id=room_id,
        position_seconds=42.0,
        anchor_ts_ms=2000,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    assert playback.status == PlaybackStatusType.PAUSED
    assert playback.position_seconds == 42.0


async def test_manual_play_is_rejected_while_someone_is_stalling_in_auto_pause_mode() -> None:
    service = RoomVideoRuntimeService()
    room_id = 505

    await service.set_room_video_source(
        room_id=room_id,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
    )
    await service.report_user_player_status(
        room_id=room_id,
        user_id=1,
        status=UserPlayerStatusType.STALLING,
        reported_at_ms=1000,
        sync_policy=RoomSyncPolicy.AUTO_PAUSE,
    )

    with pytest.raises(BadRequestError):
        await service.play(
            room_id=room_id,
            position_seconds=0.0,
            anchor_ts_ms=1100,
            sync_policy=RoomSyncPolicy.AUTO_PAUSE,
        )
