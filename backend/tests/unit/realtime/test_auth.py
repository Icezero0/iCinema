from types import SimpleNamespace

import pytest

from app.core.exceptions import UnauthorizedError
from app.realtime.auth import authenticate_websocket_token
from app.realtime.handlers.auth import AuthHandler
from app.realtime.manager import WsConnection


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent_json: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent_json.append(payload)


class FakeManager:
    def __init__(self) -> None:
        self.register_calls: list[dict] = []

    async def register_connection(self, *, user_id: int, websocket) -> WsConnection:
        self.register_calls.append({"user_id": user_id, "websocket": websocket})
        return WsConnection(
            connection_id="conn-auth",
            user_id=user_id,
            websocket=websocket,
        )


# authenticate_websocket_token 会把合法 access token 解析为用户对象
async def test_authenticate_websocket_token_returns_user_for_valid_access_token(monkeypatch) -> None:
    async def fake_get_by_id(self, db, user_id):  # noqa: ANN001
        return SimpleNamespace(id=user_id)

    monkeypatch.setattr("app.realtime.auth.decode_token", lambda token: {"type": "access", "sub": "42"})
    monkeypatch.setattr("app.realtime.auth.UserRepository.get_by_id", fake_get_by_id)

    user = await authenticate_websocket_token(db=object(), token="valid-token")

    assert user.id == 42


# authenticate_websocket_token 会拒绝非 access 类型的 token
async def test_authenticate_websocket_token_rejects_non_access_token(monkeypatch) -> None:
    monkeypatch.setattr("app.realtime.auth.decode_token", lambda token: {"type": "refresh", "sub": "42"})

    with pytest.raises(UnauthorizedError) as exc_info:
        await authenticate_websocket_token(db=object(), token="refresh-token")

    assert exc_info.value.message == "Invalid token type"


# authenticate_websocket_token 会把 token 解码失败转换为 UnauthorizedError。
async def test_authenticate_websocket_token_rejects_decode_errors(monkeypatch) -> None:
    def fake_decode_token(token):  # noqa: ANN001
        raise ValueError("expired")

    monkeypatch.setattr("app.realtime.auth.decode_token", fake_decode_token)

    with pytest.raises(UnauthorizedError) as exc_info:
        await authenticate_websocket_token(db=object(), token="expired-token")

    assert exc_info.value.message == "Invalid token"


# AuthHandler 在连接已认证时会直接返回原连接并发送 ack
async def test_auth_handler_returns_existing_connection_when_already_authenticated() -> None:
    websocket = FakeWebSocket()
    manager = FakeManager()
    connection = WsConnection(connection_id="conn-1", user_id=1, websocket=websocket)

    result = await AuthHandler().handle(
        db=object(),
        manager=manager,
        websocket=websocket,
        connection=connection,
        payload={"token": "ignored"},
    )

    assert result is connection
    assert len(websocket.sent_json) == 1
    assert manager.register_calls == []


# AuthHandler 会在首次认证时校验 token、注册连接并返回新的连接对象
async def test_auth_handler_registers_connection_after_successful_authentication(monkeypatch) -> None:
    websocket = FakeWebSocket()
    manager = FakeManager()

    async def fake_authenticate(db, *, token):  # noqa: ANN001
        assert token == "access-token"
        return SimpleNamespace(id=99)

    monkeypatch.setattr(
        "app.realtime.handlers.auth.authenticate_websocket_token",
        fake_authenticate,
    )

    result = await AuthHandler().handle(
        db=object(),
        manager=manager,
        websocket=websocket,
        connection=None,
        payload={"token": "access-token"},
    )

    assert result.user_id == 99
    assert manager.register_calls == [{"user_id": 99, "websocket": websocket}]
    assert len(websocket.sent_json) == 1
