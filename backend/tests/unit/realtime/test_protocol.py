from app.realtime.constants import (
    WsErrorCode,
    WsEventType,
    WsHeartbeatAction,
    WsMessageType,
)
from app.realtime.protocol import (
    WsMessage,
    build_ack_message,
    build_error_message,
    build_event_message,
    build_pong_message,
)


# build_event_message 会生成带有事件负载的标准消息结构
def test_build_event_message_returns_standard_event_message() -> None:
    message = build_event_message(
        event=WsEventType.ROOM_USER_PRESENCE,
        data={"room_id": 1},
    )

    assert message.type == WsMessageType.EVENT
    assert message.payload == {
        "event": WsEventType.ROOM_USER_PRESENCE,
        "data": {"room_id": 1},
    }


# build_ack_message 会保留 request_id 和 data 作为确认消息
def test_build_ack_message_returns_standard_ack_message() -> None:
    message = build_ack_message(
        request_id="req-1",
        data={"ok": True},
    )

    assert message.type == WsMessageType.ACK
    assert message.payload == {
        "request_id": "req-1",
        "data": {"ok": True},
    }


# build_error_message 会生成统一的错误消息结构
def test_build_error_message_returns_standard_error_message() -> None:
    message = build_error_message(
        code=WsErrorCode.BAD_REQUEST,
        request_id="req-2",
        reason="bad_input",
        message="bad input",
        details={"field": "name"},
    )

    assert message.type == WsMessageType.ERROR
    assert message.payload == {
        "request_id": "req-2",
        "code": WsErrorCode.BAD_REQUEST,
        "reason": "bad_input",
        "message": "bad input",
        "details": {"field": "name"},
    }


# build_pong_message 会生成服务端 heartbeat pong 响应
def test_build_pong_message_returns_heartbeat_pong_message() -> None:
    message = build_pong_message()

    assert message.type == WsMessageType.HEARTBEAT
    assert message.payload == {"action": WsHeartbeatAction.PONG}


# WsMessage 会拒绝带有未定义字段的非法消息结构
def test_ws_message_rejects_extra_fields() -> None:
    try:
        WsMessage.model_validate(
            {
                "type": WsMessageType.EVENT,
                "payload": None,
                "unexpected": True,
            }
        )
    except Exception as exc:  # noqa: BLE001
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("WsMessage should reject extra fields")
