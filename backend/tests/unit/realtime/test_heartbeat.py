import pytest

from app.core.exceptions import BadRequestError
from app.realtime.handlers.heartbeat import HeartbeatHandler
from app.realtime.protocol import build_pong_message


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent_json: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent_json.append(payload)


# HeartbeatHandler 在收到 ping 时会返回标准 pong 响应
async def test_heartbeat_handler_replies_with_pong_for_ping() -> None:
    websocket = FakeWebSocket()

    await HeartbeatHandler().handle(
        websocket=websocket,
        payload={"action": "ping"},
    )

    assert websocket.sent_json == [build_pong_message().model_dump(mode="json")]


# HeartbeatHandler 在收到非 ping 动作时会抛出业务错误
async def test_heartbeat_handler_rejects_non_ping_action() -> None:
    websocket = FakeWebSocket()

    with pytest.raises(BadRequestError) as exc_info:
        await HeartbeatHandler().handle(
            websocket=websocket,
            payload={"action": "pong"},
        )

    assert exc_info.value.message == "Client heartbeat action must be ping"
