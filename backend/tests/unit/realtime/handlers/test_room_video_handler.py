from types import SimpleNamespace

import pytest

from app.core.exceptions import BadRequestError, ForbiddenError
from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomSyncPolicy,
    RoomVideoSourceType,
)
from app.realtime.constants import AutoPlaybackAction, PlaybackStatusType, WsCommandAction
from app.realtime.handlers.room_video import RoomVideoCommandHandler, RoomVideoRuntimePolicy
from app.realtime.manager import WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.room_video_runtime import RoomVideoRuntimeService, UserResourceStatesUpdateResult
from app.realtime.state import (
    PlaybackState,
    RoomVideoSourceState,
    UserResourceStatesState,
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def publish_room_video_source_set(self, **kwargs) -> None:
        self.calls.append(("publish_room_video_source_set", kwargs))

    async def publish_playback_play(self, **kwargs) -> None:
        self.calls.append(("publish_playback_play", kwargs))

    async def publish_playback_pause(self, **kwargs) -> None:
        self.calls.append(("publish_playback_pause", kwargs))

    async def publish_playback_seek(self, **kwargs) -> None:
        self.calls.append(("publish_playback_seek", kwargs))

    async def publish_user_resource_states(self, **kwargs) -> None:
        self.calls.append(("publish_user_resource_states", kwargs))


def _build_connection(*, user_id: int, room_id: int | None) -> WsConnection:
    return WsConnection(
        connection_id=f"conn-{user_id}",
        user_id=user_id,
        websocket=SimpleNamespace(),
        active_room_id=room_id,
    )


# 未进入房间时不能控制房间视频
def test_require_active_room_rejects_connection_without_active_room() -> None:
    connection = _build_connection(user_id=1, room_id=None)

    with pytest.raises(BadRequestError) as exc_info:
        RoomVideoCommandHandler._require_active_room(connection)

    assert exc_info.value.message == "You must enter a room before controlling room video"


# 权限不足的角色不能控制需要管理权限的视频同步
def test_require_active_sync_permission_rejects_role_without_permission() -> None:
    with pytest.raises(ForbiddenError) as exc_info:
        RoomVideoCommandHandler._require_active_sync_permission(
            role="member",
            permission=RoomActiveSyncPermission.OWNER_AND_MANAGER,
        )

    assert exc_info.value.message == "You do not have permission to control room video"


# 资源健康状态只接受 ready / stalling / error，废弃旧 idle 状态
def test_parse_resource_health_status_rejects_idle() -> None:
    with pytest.raises(BadRequestError) as exc_info:
        RoomVideoCommandHandler._parse_resource_health_status("idle")

    assert exc_info.value.message == "Invalid status"


# 用户没有房间角色时不能控制房间视频
async def test_handle_rejects_user_without_room_role(monkeypatch) -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    connection = _build_connection(user_id=2, room_id=20)
    command = WsCommandPayload(
        request_id="req-1",
        action=WsCommandAction.PLAYBACK_PLAY,
        data={"position_seconds": 1.0, "anchor_ts_ms": 1000},
    )

    async def fake_get_room_by_id(db, room_id):  # noqa: ANN001
        return SimpleNamespace(id=room_id)

    async def fake_find_room_role(db, room_id, user_id):  # noqa: ANN001
        return None

    monkeypatch.setattr(handler.room_service, "get_room_by_id", fake_get_room_by_id)
    monkeypatch.setattr(handler.membership_service, "find_room_role", fake_find_room_role)

    with pytest.raises(ForbiddenError) as exc_info:
        await handler.handle(
            db=object(),
            manager=object(),
            publisher=RecordingPublisher(),
            connection=connection,
            command=command,
        )

    assert exc_info.value.message == "You are not allowed to control room video in this room"


# USER_RESOURCE_STATUS 会上报资源健康聚合状态并在需要时广播自动暂停
async def test_handle_user_resource_status_publishes_resource_states_and_auto_pause(monkeypatch) -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    publisher = RecordingPublisher()
    connection = _build_connection(user_id=3, room_id=30)
    command = WsCommandPayload(
        request_id="req-2",
        action=WsCommandAction.USER_RESOURCE_STATUS,
        data={"status": "stalling", "reported_at_ms": 1000},
    )
    playback = PlaybackState(
        room_id=30,
        status=PlaybackStatusType.PAUSED,
        position_seconds=9.0,
        anchor_ts_ms=2000,
        playback_rate=1.0,
    )
    update_result = UserResourceStatesUpdateResult(
        user_resource_states=UserResourceStatesState(room_id=30, user_resource_states=[]),
        auto_playback=playback,
        auto_action=AutoPlaybackAction.PAUSE,
    )

    async def fake_get_room_by_id(db, room_id):  # noqa: ANN001
        return SimpleNamespace(id=room_id)

    async def fake_find_room_role(db, room_id, user_id):  # noqa: ANN001
        return "member"

    async def fake_get_runtime_policy(*, db, room_id):  # noqa: ANN001
        return RoomVideoRuntimePolicy(
            sync_policy=RoomSyncPolicy.AUTO_SYNC,
            active_sync_permission=RoomActiveSyncPermission.ALL_MEMBERS,
        )

    async def fake_report_user_resource_status(**kwargs):  # noqa: ANN001
        return update_result

    monkeypatch.setattr(handler.room_service, "get_room_by_id", fake_get_room_by_id)
    monkeypatch.setattr(handler.membership_service, "find_room_role", fake_find_room_role)
    monkeypatch.setattr(handler, "_get_runtime_policy", fake_get_runtime_policy)
    monkeypatch.setattr(
        handler.video_runtime_service,
        "report_user_resource_status",
        fake_report_user_resource_status,
    )

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=publisher,
        connection=connection,
        command=command,
    )

    assert result == {
        "user_resource_states": {"room_id": 30, "user_resource_states": []},
        "playback": playback.model_dump(mode="json"),
        "auto_action": "pause",
    }
    assert publisher.calls[0][0] == "publish_user_resource_states"
    assert publisher.calls[1] == ("publish_playback_pause", {"playback": playback})


# 设置外链视频源时会更新 runtime 并广播视频源和播放状态
async def test_handle_room_video_source_set_for_external_url(monkeypatch) -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    publisher = RecordingPublisher()
    command = WsCommandPayload(
        request_id="req-3",
        action=WsCommandAction.ROOM_VIDEO_SOURCE_SET,
        data={
            "source_type": "external_url",
            "external_url": "https://example.com/video.mp4",
            "anchor_ts_ms": 1234,
        },
    )
    room_video_source = RoomVideoSourceState(
        room_id=40,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
        file_hash=None,
    )
    playback = PlaybackState(
        room_id=40,
        status=PlaybackStatusType.PAUSED,
        position_seconds=0.0,
        anchor_ts_ms=1234,
        playback_rate=1.0,
    )
    user_resource_states = UserResourceStatesState(room_id=40, user_resource_states=[])

    async def fake_set_selected_room_video_source_type(db, room_id, source_type):  # noqa: ANN001
        return SimpleNamespace()

    async def fake_set_room_video_source(**kwargs):  # noqa: ANN001
        return room_video_source, playback, user_resource_states

    monkeypatch.setattr(
        handler.room_settings_service,
        "set_selected_room_video_source_type",
        fake_set_selected_room_video_source_type,
    )
    monkeypatch.setattr(
        handler.video_runtime_service,
        "set_room_video_source",
        fake_set_room_video_source,
    )

    result = await handler._handle_room_video_source_set(
        db=object(),
        publisher=publisher,
        room_id=40,
        command=command,
    )

    assert result == {
        "room_video_source": room_video_source.model_dump(mode="json"),
        "playback": playback.model_dump(mode="json"),
        "user_resource_states": user_resource_states.model_dump(mode="json"),
    }
    assert publisher.calls[0] == ("publish_room_video_source_set", {"room_video_source": room_video_source})
    assert publisher.calls[1] == ("publish_playback_pause", {"playback": playback})
    assert publisher.calls[2] == (
        "publish_user_resource_states",
        {"user_resource_states": user_resource_states},
    )


# 外链视频源不允许同时传 file_hash
async def test_handle_room_video_source_set_rejects_file_hash_for_external_url() -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    command = WsCommandPayload(
        request_id="req-4",
        action=WsCommandAction.ROOM_VIDEO_SOURCE_SET,
        data={
            "source_type": "external_url",
            "external_url": "https://example.com/video.mp4",
            "file_hash": "abc",
        },
    )

    with pytest.raises(BadRequestError) as exc_info:
        await handler._handle_room_video_source_set(
            db=object(),
            publisher=RecordingPublisher(),
            room_id=50,
            command=command,
        )

    assert exc_info.value.message == "file_hash is not allowed for external_url source"


# 播放命令会调用 runtime.play 并广播播放事件
async def test_handle_play_calls_runtime_and_publishes_playback(monkeypatch) -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    publisher = RecordingPublisher()
    command = WsCommandPayload(
        request_id="req-5",
        action=WsCommandAction.PLAYBACK_PLAY,
        data={"position_seconds": 5.0, "anchor_ts_ms": 3000, "playback_rate": 1.25},
    )
    playback = PlaybackState(
        room_id=60,
        status=PlaybackStatusType.PLAYING,
        position_seconds=5.0,
        anchor_ts_ms=3000,
        playback_rate=1.25,
    )

    async def fake_play(**kwargs):  # noqa: ANN001
        assert kwargs["sync_policy"] == RoomSyncPolicy.AUTO_SYNC
        return playback

    monkeypatch.setattr(handler.video_runtime_service, "play", fake_play)

    result = await handler._handle_play(
        publisher=publisher,
        room_id=60,
        command=command,
        sync_policy=RoomSyncPolicy.AUTO_SYNC,
    )

    assert result == {"playback": playback.model_dump(mode="json")}
    assert publisher.calls == [("publish_playback_play", {"playback": playback})]


# seek 命令会调用 runtime.seek 并广播 seek 事件
async def test_handle_seek_calls_runtime_and_publishes_seek(monkeypatch) -> None:
    handler = RoomVideoCommandHandler(video_runtime_service=RoomVideoRuntimeService())
    publisher = RecordingPublisher()
    command = WsCommandPayload(
        request_id="req-6",
        action=WsCommandAction.PLAYBACK_SEEK,
        data={"position_seconds": 12.0, "anchor_ts_ms": 4000},
    )
    playback = PlaybackState(
        room_id=61,
        status=PlaybackStatusType.PAUSED,
        position_seconds=12.0,
        anchor_ts_ms=4000,
        playback_rate=1.0,
    )

    async def fake_seek(**kwargs):  # noqa: ANN001
        return playback

    monkeypatch.setattr(handler.video_runtime_service, "seek", fake_seek)

    result = await handler._handle_seek(
        publisher=publisher,
        room_id=61,
        command=command,
        sync_policy=RoomSyncPolicy.AUTO_SYNC,
    )

    assert result == {"playback": playback.model_dump(mode="json")}
    assert publisher.calls == [("publish_playback_seek", {"playback": playback})]
