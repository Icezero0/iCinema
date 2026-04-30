from types import SimpleNamespace

import pytest

from app.core.exceptions import BadRequestError, ForbiddenError
from app.modules.rooms.constants import RoomSyncPolicy, RoomVideoSourceType
from app.realtime.constants import AutoPlaybackAction, PlaybackStatusType, WsCommandAction
from app.realtime.handlers.room import RoomCommandHandler
from app.realtime.manager import WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomSessionExitResult, RoomVideoRuntimeService
from app.realtime.state import (
    PlaybackState,
    PresenceState,
    RoomVideoSourceState,
    UserResourceStatesState,
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def publish_session_closed(self, **kwargs) -> None:
        self.calls.append(("publish_session_closed", kwargs))

    async def publish_room_user_presence(self, **kwargs) -> None:
        self.calls.append(("publish_room_user_presence", kwargs))

    async def publish_user_resource_states(self, **kwargs) -> None:
        self.calls.append(("publish_user_resource_states", kwargs))

    async def publish_playback_play(self, **kwargs) -> None:
        self.calls.append(("publish_playback_play", kwargs))


# 缺少 room_id 时会拒绝房间命令
def test_extract_room_id_rejects_missing_room_id() -> None:
    command = WsCommandPayload(request_id="req-1", action=WsCommandAction.ROOM_ENTER, data={})

    with pytest.raises(BadRequestError) as exc_info:
        RoomCommandHandler._extract_room_id(command)

    assert exc_info.value.message == "room_id is required"


# 非正整数 room_id 会被拒绝
def test_extract_room_id_rejects_non_positive_room_id() -> None:
    command = WsCommandPayload(
        request_id="req-2",
        action=WsCommandAction.ROOM_ENTER,
        data={"room_id": 0},
    )

    with pytest.raises(BadRequestError) as exc_info:
        RoomCommandHandler._extract_room_id(command)

    assert exc_info.value.message == "room_id must be a positive integer"


# 未进入房间时不能主动查询房间运行时
def test_require_active_room_rejects_connection_without_active_room() -> None:
    connection = WsConnection(
        connection_id="conn-no-room",
        user_id=1,
        websocket=SimpleNamespace(),
    )

    with pytest.raises(BadRequestError) as exc_info:
        RoomCommandHandler._require_active_room(connection)

    assert exc_info.value.message == "You must enter a room before querying room runtime"


# room_presence_get 返回当前房间在线成员状态
async def test_handle_room_presence_get_returns_presence(monkeypatch) -> None:
    handler = RoomCommandHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    connection = WsConnection(
        connection_id="conn-presence",
        user_id=1,
        websocket=SimpleNamespace(),
        active_room_id=10,
    )
    command = WsCommandPayload(
        request_id="req-presence",
        action=WsCommandAction.ROOM_PRESENCE_GET,
        data=None,
    )
    presence = PresenceState(room_id=10, present_user_ids=[1, 2])

    async def fake_get_presence_state(*, room_id):  # noqa: ANN001
        assert room_id == 10
        return presence

    monkeypatch.setattr(handler.presence_service, "get_presence_state", fake_get_presence_state)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=RecordingPublisher(),
        connection=connection,
        command=command,
    )

    assert result == {"presence": presence.model_dump(mode="json")}


# room_video_runtime_get 返回当前房间播放同步运行时，不夹带 presence
async def test_handle_room_video_runtime_get_returns_video_runtime(monkeypatch) -> None:
    runtime_service = RoomVideoRuntimeService()
    handler = RoomCommandHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=runtime_service,
    )
    connection = WsConnection(
        connection_id="conn-video-runtime",
        user_id=1,
        websocket=SimpleNamespace(),
        active_room_id=11,
    )
    command = WsCommandPayload(
        request_id="req-video-runtime",
        action=WsCommandAction.ROOM_VIDEO_RUNTIME_GET,
        data=None,
    )
    room_video_source = RoomVideoSourceState(
        room_id=11,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
        file_hash=None,
    )
    playback = PlaybackState(
        room_id=11,
        status=PlaybackStatusType.PAUSED,
        position_seconds=3.5,
        anchor_ts_ms=1000,
        playback_rate=1.0,
    )
    resource_states = UserResourceStatesState(room_id=11, user_resource_states=[])

    async def fake_get_room_video_source(*, room_id):  # noqa: ANN001
        assert room_id == 11
        return room_video_source

    async def fake_get_playback(*, room_id):  # noqa: ANN001
        assert room_id == 11
        return playback

    async def fake_get_user_resource_states(*, room_id):  # noqa: ANN001
        assert room_id == 11
        return resource_states

    monkeypatch.setattr(runtime_service, "get_room_video_source", fake_get_room_video_source)
    monkeypatch.setattr(runtime_service, "get_playback", fake_get_playback)
    monkeypatch.setattr(runtime_service, "get_user_resource_states", fake_get_user_resource_states)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=RecordingPublisher(),
        connection=connection,
        command=command,
    )

    assert result == {
        "room_video_source": room_video_source.model_dump(mode="json"),
        "playback": playback.model_dump(mode="json"),
        "user_resource_states": resource_states.model_dump(mode="json"),
    }
    assert "presence" not in result


# 没有房间角色时不能进入房间
async def test_handle_room_enter_rejects_user_without_room_role(monkeypatch) -> None:
    handler = RoomCommandHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    connection = WsConnection(connection_id="conn-1", user_id=1, websocket=SimpleNamespace())
    command = WsCommandPayload(
        request_id="req-3",
        action=WsCommandAction.ROOM_ENTER,
        data={"room_id": 10},
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

    assert exc_info.value.message == "You are not allowed to enter this room"


# 进入房间会返回快照并广播顶号会话和房间 presence
async def test_handle_room_enter_returns_snapshot_and_publishes_presence(monkeypatch) -> None:
    presence_service = RoomPresenceService()
    runtime_service = RoomVideoRuntimeService()
    handler = RoomCommandHandler(
        presence_service=presence_service,
        video_runtime_service=runtime_service,
    )
    publisher = RecordingPublisher()
    connection = WsConnection(connection_id="conn-2", user_id=2, websocket=SimpleNamespace())
    command = WsCommandPayload(
        request_id="req-4",
        action=WsCommandAction.ROOM_ENTER,
        data={"room_id": 20},
    )
    room_video_source = RoomVideoSourceState(
        room_id=20,
        source_type=RoomVideoSourceType.EXTERNAL_URL,
        external_url="https://example.com/video.mp4",
        file_hash=None,
    )
    playback = PlaybackState(
        room_id=20,
        status=PlaybackStatusType.PAUSED,
        position_seconds=0.0,
        anchor_ts_ms=1000,
        playback_rate=1.0,
    )
    resource_states = UserResourceStatesState(room_id=20, user_resource_states=[])

    async def fake_get_room_by_id(db, room_id):  # noqa: ANN001
        return SimpleNamespace(id=room_id)

    async def fake_find_room_role(db, room_id, user_id):  # noqa: ANN001
        return "member"

    async def fake_find_room_user_connection(*, room_id, user_id):  # noqa: ANN001
        return "old-conn"

    async def fake_enter_room(*, manager, connection, room_id):  # noqa: ANN001
        connection.active_room_id = room_id
        return PresenceState(room_id=room_id, present_user_ids=[2])

    async def fake_get_room_video_source(*, room_id):  # noqa: ANN001
        return room_video_source

    async def fake_get_playback(*, room_id):  # noqa: ANN001
        return playback

    async def fake_get_user_resource_states(*, room_id):  # noqa: ANN001
        return resource_states

    monkeypatch.setattr(handler.room_service, "get_room_by_id", fake_get_room_by_id)
    monkeypatch.setattr(handler.membership_service, "find_room_role", fake_find_room_role)
    monkeypatch.setattr(presence_service, "find_room_user_connection", fake_find_room_user_connection)
    monkeypatch.setattr(presence_service, "enter_room", fake_enter_room)
    monkeypatch.setattr(runtime_service, "get_room_video_source", fake_get_room_video_source)
    monkeypatch.setattr(runtime_service, "get_playback", fake_get_playback)
    monkeypatch.setattr(runtime_service, "get_user_resource_states", fake_get_user_resource_states)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=publisher,
        connection=connection,
        command=command,
    )

    assert result == {
        "room_id": 20,
        "present_user_ids": [2],
        "room_video_source": room_video_source.model_dump(mode="json"),
        "playback": playback.model_dump(mode="json"),
        "user_resource_states": resource_states.model_dump(mode="json"),
    }
    assert publisher.calls[0] == (
        "publish_session_closed",
        {"connection_id": "old-conn", "room_id": 20, "reason": "entered_elsewhere"},
    )
    assert publisher.calls[1] == (
        "publish_room_user_presence",
        {
            "presence": PresenceState(room_id=20, present_user_ids=[2]),
            "exclude_connection_ids": {"conn-2"},
        },
    )


# 离开房间失败时不会触发任何广播
async def test_handle_room_leave_returns_without_publishing_when_leave_fails(monkeypatch) -> None:
    handler = RoomCommandHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    publisher = RecordingPublisher()
    connection = WsConnection(connection_id="conn-3", user_id=3, websocket=SimpleNamespace())
    command = WsCommandPayload(
        request_id="req-5",
        action=WsCommandAction.ROOM_LEAVE,
        data={"room_id": 30},
    )

    async def fake_leave_room(*, manager, connection, room_id):  # noqa: ANN001
        return False

    monkeypatch.setattr(handler.presence_service, "leave_room", fake_leave_room)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=publisher,
        connection=connection,
        command=command,
    )

    assert result is None
    assert publisher.calls == []


# 离开房间后会广播 presence 和必要的自动恢复播放结果
async def test_handle_room_leave_publishes_session_exit_updates(monkeypatch) -> None:
    handler = RoomCommandHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    publisher = RecordingPublisher()
    connection = WsConnection(connection_id="conn-4", user_id=4, websocket=SimpleNamespace())
    command = WsCommandPayload(
        request_id="req-6",
        action=WsCommandAction.ROOM_LEAVE,
        data={"room_id": 40},
    )
    presence = PresenceState(room_id=40, present_user_ids=[5])
    playback = PlaybackState(
        room_id=40,
        status=PlaybackStatusType.PLAYING,
        position_seconds=15.0,
        anchor_ts_ms=2000,
        playback_rate=1.0,
    )
    session_exit_result = RoomSessionExitResult(
        room_cleared=False,
        user_resource_states=UserResourceStatesState(room_id=40, user_resource_states=[]),
        auto_playback=playback,
        auto_action=AutoPlaybackAction.PLAY,
    )

    async def fake_leave_room(*, manager, connection, room_id):  # noqa: ANN001
        return True

    async def fake_get_presence_state(*, room_id):  # noqa: ANN001
        return presence

    async def fake_get_room_sync_policy(*, db, room_id):  # noqa: ANN001
        return RoomSyncPolicy.AUTO_SYNC

    async def fake_handle_room_session_exit(*, room_id, user_id, sync_policy, room_empty):  # noqa: ANN001
        assert room_empty is False
        return session_exit_result

    monkeypatch.setattr(handler.presence_service, "leave_room", fake_leave_room)
    monkeypatch.setattr(handler.presence_service, "get_presence_state", fake_get_presence_state)
    monkeypatch.setattr(handler, "_get_room_sync_policy", fake_get_room_sync_policy)
    monkeypatch.setattr(
        handler.video_runtime_service,
        "handle_room_session_exit",
        fake_handle_room_session_exit,
    )

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=publisher,
        connection=connection,
        command=command,
    )

    assert result is None
    assert publisher.calls[0][0] == "publish_user_resource_states"
    assert publisher.calls[1] == ("publish_playback_play", {"playback": playback})
    assert publisher.calls[2] == (
        "publish_room_user_presence",
        {"presence": presence, "exclude_connection_ids": {"conn-4"}},
    )
