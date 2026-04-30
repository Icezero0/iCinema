import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import WebSocketDisconnect

from app.realtime.manager import WsConnection
from app.realtime.ws_router import websocket_endpoint


class _DummySessionContext:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeWebSocket:
    def __init__(self, app, messages=None):
        self.app = app
        self._messages = list(messages or [])
        self.accept = AsyncMock()
        self.close = AsyncMock()

    async def receive_json(self):
        if self._messages:
            next_item = self._messages.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            return next_item
        raise WebSocketDisconnect()


# 验证 websocket 在认证超时前未收到认证消息时会主动关闭连接。
async def test_websocket_endpoint_closes_on_auth_timeout(monkeypatch) -> None:
    app = SimpleNamespace(
        state=SimpleNamespace(
            realtime_manager=SimpleNamespace(),
            realtime_publisher=SimpleNamespace(),
            realtime_room_presence_service=SimpleNamespace(),
            realtime_room_video_runtime_service=SimpleNamespace(),
        )
    )
    ws = _FakeWebSocket(app=app)

    monotonic_values = [100.0, 111.0]

    def fake_monotonic():
        if monotonic_values:
            return monotonic_values.pop(0)
        return 111.0

    monkeypatch.setattr("app.realtime.ws_router.time.monotonic", fake_monotonic)

    await websocket_endpoint(ws)

    ws.accept.assert_awaited_once()
    ws.close.assert_awaited_once_with(code=1008, reason="Authentication timeout")


# 验证 websocket 断开连接后会清理连接、刷新房间状态并广播在线信息。
async def test_websocket_endpoint_disconnect_cleanup_publishes_presence(monkeypatch) -> None:
    connection = WsConnection(
        connection_id="conn-1",
        user_id=7,
        websocket=SimpleNamespace(),
        active_room_id=42,
    )
    presence = SimpleNamespace(room_id=42, present_user_ids={1, 2})
    publisher = SimpleNamespace(
        publish_user_resource_states=AsyncMock(),
        publish_playback_play=AsyncMock(),
        publish_room_user_presence=AsyncMock(),
    )
    manager = SimpleNamespace(disconnect=AsyncMock())
    presence_service = SimpleNamespace(
        handle_disconnect=AsyncMock(return_value=42),
        get_presence_state=AsyncMock(return_value=presence),
    )
    session_exit_result = SimpleNamespace(
        room_cleared=False,
        user_resource_states={"states": []},
        auto_action="pause",
        auto_playback=None,
    )
    video_runtime_service = SimpleNamespace(
        handle_room_session_exit=AsyncMock(return_value=session_exit_result),
    )
    app = SimpleNamespace(
        state=SimpleNamespace(
            realtime_manager=manager,
            realtime_publisher=publisher,
            realtime_room_presence_service=presence_service,
            realtime_room_video_runtime_service=video_runtime_service,
        )
    )
    ws = _FakeWebSocket(
        app=app,
        messages=[{"type": "auth"}, WebSocketDisconnect()],
    )

    class _FakeHandler:
        def __init__(self, **kwargs):
            pass

        async def handle(self, **kwargs):
            return connection

    monkeypatch.setattr("app.realtime.ws_router.RealtimeMessageHandler", _FakeHandler)
    monkeypatch.setattr("app.realtime.ws_router.AsyncSessionLocal", lambda: _DummySessionContext())
    monkeypatch.setattr(
        "app.realtime.ws_router.RoomSettingsService",
        lambda: SimpleNamespace(
            find_room_settings_by_room_id=AsyncMock(
                return_value=SimpleNamespace(sync_policy="auto_sync")
            )
        ),
    )

    await websocket_endpoint(ws)

    ws.accept.assert_awaited_once()
    presence_service.handle_disconnect.assert_awaited_once_with(connection=connection)
    manager.disconnect.assert_awaited_once_with(connection.connection_id)
    publisher.publish_user_resource_states.assert_awaited_once_with(
        user_resource_states={"states": []}
    )
    publisher.publish_room_user_presence.assert_awaited_once_with(presence=presence)
