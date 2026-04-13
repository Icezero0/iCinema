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
