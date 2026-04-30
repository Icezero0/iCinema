from types import SimpleNamespace

from app.core.exceptions import BadRequestError
from app.realtime.constants import WsCommandAction, WsErrorCode
from app.realtime.handlers.dispatcher import RealtimeMessageHandler
from app.realtime.manager import WsConnection
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent_json: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent_json.append(payload)


# 认证消息会分发给 AuthHandler 并返回新的连接对象
async def test_dispatcher_routes_auth_message_to_auth_handler(monkeypatch) -> None:
    websocket = FakeWebSocket()
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    expected_connection = WsConnection(
        connection_id="conn-auth",
        user_id=1,
        websocket=websocket,
    )

    async def fake_auth_handle(**kwargs):  # noqa: ANN001
        return expected_connection

    monkeypatch.setattr(handler.auth_handler, "handle", fake_auth_handle)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=object(),
        websocket=websocket,
        connection=None,
        raw_message={"type": "auth", "payload": {"token": "abc"}},
    )

    assert result is expected_connection


# heartbeat 消息会分发给 HeartbeatHandler 且不会改变连接对象
async def test_dispatcher_routes_heartbeat_message_to_heartbeat_handler(monkeypatch) -> None:
    websocket = FakeWebSocket()
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    connection = WsConnection(connection_id="conn-heartbeat", user_id=2, websocket=websocket)
    called = {"value": False}

    async def fake_heartbeat_handle(**kwargs):  # noqa: ANN001
        called["value"] = True

    monkeypatch.setattr(handler.heartbeat_handler, "handle", fake_heartbeat_handle)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=object(),
        websocket=websocket,
        connection=connection,
        raw_message={"type": "heartbeat", "payload": {"action": "ping"}},
    )

    assert result is connection
    assert called["value"] is True


# 命令消息在分发成功后会返回带 request_id 的 ack
async def test_dispatcher_sends_ack_after_command_dispatch(monkeypatch) -> None:
    websocket = FakeWebSocket()
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    connection = WsConnection(connection_id="conn-command", user_id=3, websocket=websocket)

    async def fake_dispatch_command(**kwargs):  # noqa: ANN001
        return {"ok": True}

    monkeypatch.setattr(handler, "_dispatch_command", fake_dispatch_command)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=object(),
        websocket=websocket,
        connection=connection,
        raw_message={
            "type": "command",
            "payload": {
                "request_id": "req-1",
                "action": "room_leave",
                "data": {"room_id": 1},
            },
        },
    )

    assert result is connection
    assert websocket.sent_json[0]["type"] == "ack"
    assert websocket.sent_json[0]["payload"] == {
        "request_id": "req-1",
        "data": {"ok": True},
    }


# 未认证时发送命令会返回带 request_id 的错误消息
async def test_dispatcher_rejects_command_before_authentication() -> None:
    websocket = FakeWebSocket()
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=object(),
        websocket=websocket,
        connection=None,
        raw_message={
            "type": "command",
            "payload": {
                "request_id": "req-2",
                "action": "room_leave",
                "data": {"room_id": 1},
            },
        },
    )

    assert result is None
    assert websocket.sent_json[0]["type"] == "error"
    assert websocket.sent_json[0]["payload"] == {
        "request_id": "req-2",
        "code": "bad_request",
        "reason": "authentication_required",
        "message": "Authentication required before this action",
        "details": None,
    }


# 非法消息结构会返回 INVALID_PAYLOAD 错误
async def test_dispatcher_returns_invalid_payload_error_for_malformed_message() -> None:
    websocket = FakeWebSocket()
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    connection = WsConnection(connection_id="conn-invalid", user_id=4, websocket=websocket)

    result = await handler.handle(
        db=object(),
        manager=object(),
        publisher=object(),
        websocket=websocket,
        connection=connection,
        raw_message={"type": "command", "payload": {"request_id": "req-3"}},
    )

    assert result is connection
    assert websocket.sent_json[0]["payload"]["code"] == WsErrorCode.INVALID_PAYLOAD
    assert websocket.sent_json[0]["payload"]["reason"] == "invalid_websocket_payload"
    assert "errors" in websocket.sent_json[0]["payload"]["details"]


# _dispatch_command 会把房间命令路由给 RoomCommandHandler
async def test_dispatcher_routes_room_actions_to_room_handler(monkeypatch) -> None:
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    called = {"value": False}

    async def fake_room_handle(**kwargs):  # noqa: ANN001
        called["value"] = True
        return {"room": True}

    monkeypatch.setattr(handler.room_handler, "handle", fake_room_handle)

    result = await handler._dispatch_command(
        db=object(),
        manager=object(),
        publisher=object(),
        connection=SimpleNamespace(),
        command=SimpleNamespace(action=WsCommandAction.ROOM_ENTER),
    )

    assert result == {"room": True}
    assert called["value"] is True


# _dispatch_command 会把播放相关命令路由给 RoomVideoCommandHandler
async def test_dispatcher_routes_video_actions_to_room_video_handler(monkeypatch) -> None:
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )
    called = {"value": False}

    async def fake_room_video_handle(**kwargs):  # noqa: ANN001
        called["value"] = True
        return {"video": True}

    monkeypatch.setattr(handler.room_video_handler, "handle", fake_room_video_handle)

    result = await handler._dispatch_command(
        db=object(),
        manager=object(),
        publisher=object(),
        connection=SimpleNamespace(),
        command=SimpleNamespace(action=WsCommandAction.PLAYBACK_PLAY),
    )

    assert result == {"video": True}
    assert called["value"] is True


# _dispatch_command 会拒绝未支持的命令动作
async def test_dispatcher_rejects_unsupported_command_action() -> None:
    handler = RealtimeMessageHandler(
        presence_service=RoomPresenceService(),
        video_runtime_service=RoomVideoRuntimeService(),
    )

    try:
        await handler._dispatch_command(
            db=object(),
            manager=object(),
            publisher=object(),
            connection=SimpleNamespace(),
            command=SimpleNamespace(action="unsupported_action"),
        )
    except BadRequestError as exc:
        assert exc.message == "Unsupported command action: unsupported_action"
    else:
        raise AssertionError("Unsupported command action should raise BadRequestError")
