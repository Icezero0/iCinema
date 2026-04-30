from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.realtime.constants import AutoPlaybackAction
from app.realtime.rest_sync import close_room_sessions, close_room_user_session


# 验证关闭房间用户会话时，如果没有活动连接则不会执行后续动作。
async def test_close_room_user_session_returns_false_when_connection_missing(
    db_session,
) -> None:
    presence_service = SimpleNamespace(
        find_room_user_connection=AsyncMock(return_value=None),
    )

    result = await close_room_user_session(
        db=db_session,
        manager=SimpleNamespace(),
        publisher=SimpleNamespace(),
        presence_service=presence_service,
        video_runtime_service=SimpleNamespace(),
        room_id=1,
        user_id=2,
        reason="removed",
    )

    assert result is False


# 验证关闭房间用户会话时会发布会话关闭、运行时和在线状态更新。
async def test_close_room_user_session_publishes_presence_and_runtime_updates(
    db_session,
    monkeypatch,
) -> None:
    publisher = SimpleNamespace(
        publish_session_closed=AsyncMock(),
        publish_user_resource_states=AsyncMock(),
        publish_playback_play=AsyncMock(),
        publish_room_user_presence=AsyncMock(),
    )
    presence = SimpleNamespace(room_id=1, present_user_ids={10})
    presence_service = SimpleNamespace(
        find_room_user_connection=AsyncMock(return_value="conn-1"),
        evict_room_user=AsyncMock(return_value="conn-1"),
        get_presence_state=AsyncMock(return_value=presence),
    )
    runtime_result = SimpleNamespace(
        room_cleared=False,
        user_resource_states={"items": [1]},
        auto_action=AutoPlaybackAction.PLAY,
        auto_playback={"position": 3},
    )
    video_runtime_service = SimpleNamespace(
        handle_room_session_exit=AsyncMock(return_value=runtime_result),
    )

    settings_service = SimpleNamespace(
        find_room_settings_by_room_id=AsyncMock(
            return_value=SimpleNamespace(sync_policy="auto_sync")
        )
    )
    monkeypatch.setattr(
        "app.realtime.rest_sync.RoomSettingsService",
        lambda: settings_service,
    )

    result = await close_room_user_session(
        db=db_session,
        manager=SimpleNamespace(),
        publisher=publisher,
        presence_service=presence_service,
        video_runtime_service=video_runtime_service,
        room_id=1,
        user_id=10,
        reason="removed",
    )

    assert result is True
    publisher.publish_session_closed.assert_awaited_once()
    publisher.publish_user_resource_states.assert_awaited_once_with(
        user_resource_states={"items": [1]}
    )
    publisher.publish_playback_play.assert_awaited_once_with(playback={"position": 3})
    publisher.publish_room_user_presence.assert_awaited_once_with(presence=presence)


# 验证关闭房间全部会话时，即使没有活动连接也会清理运行时。
async def test_close_room_sessions_clears_runtime_even_without_connections() -> None:
    video_runtime_service = SimpleNamespace(clear_room_runtime=AsyncMock())

    closed_user_ids = await close_room_sessions(
        manager=SimpleNamespace(),
        publisher=SimpleNamespace(publish_session_closed=AsyncMock()),
        presence_service=SimpleNamespace(evict_room_users=AsyncMock(return_value=[])),
        video_runtime_service=video_runtime_service,
        room_id=1,
        reason="room_deleted",
    )

    assert closed_user_ids == []
    video_runtime_service.clear_room_runtime.assert_awaited_once_with(room_id=1)
