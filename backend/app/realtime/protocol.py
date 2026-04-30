from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.realtime.constants import (
    WsCommandAction,
    WsErrorCode,
    WsEventType,
    WsHeartbeatAction,
    WsMessageType,
)


class WsMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v: int = 1
    type: WsMessageType
    payload: dict[str, Any] | None = None


# =========================
# client <--> server
# =========================


class WsHeartbeatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: WsHeartbeatAction


# =========================
# client ---> server
# =========================


class WsAuthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str


class WsCommandPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    action: WsCommandAction
    data: dict[str, Any] | None = None


# =========================
# client <--- server
# =========================


class WsEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: WsEventType
    data: dict[str, Any] | None = None


class WsErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None
    code: WsErrorCode
    reason: str
    message: str
    details: dict[str, Any] | None = None


class WsAckPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None
    data: dict[str, Any] | None = None


# =========================
# message builders
# =========================


def build_event_message(
    *,
    event: WsEventType,
    data: dict[str, Any] | None = None,
) -> WsMessage:
    return WsMessage(
        type=WsMessageType.EVENT,
        payload=WsEventPayload(
            event=event,
            data=data,
        ).model_dump(mode="json"),
    )


def build_ack_message(
    *,
    request_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> WsMessage:
    return WsMessage(
        type=WsMessageType.ACK,
        payload=WsAckPayload(
            request_id=request_id,
            data=data,
        ).model_dump(mode="json"),
    )


def build_error_message(
    *,
    code: WsErrorCode,
    request_id: str | None = None,
    reason: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> WsMessage:
    return WsMessage(
        type=WsMessageType.ERROR,
        payload=WsErrorPayload(
            code=code,
            request_id=request_id,
            reason=reason,
            message=message,
            details=details,
        ).model_dump(mode="json"),
    )


def build_pong_message() -> WsMessage:
    return WsMessage(
        type=WsMessageType.HEARTBEAT,
        payload=WsHeartbeatPayload(
            action=WsHeartbeatAction.PONG,
        ).model_dump(mode="json"),
    )
