from __future__ import annotations

from fastapi import WebSocket

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError
from app.realtime.constants import WsHeartbeatAction
from app.realtime.protocol import WsHeartbeatPayload, build_pong_message


class HeartbeatHandler:
    async def handle(
        self,
        *,
        websocket: WebSocket,
        payload: dict | None,
    ) -> None:
        heartbeat_payload = WsHeartbeatPayload.model_validate(payload or {})
        if heartbeat_payload.action != WsHeartbeatAction.PING:
            raise BadRequestError(
                "Client heartbeat action must be ping",
                reason=ErrorReason.INVALID_HEARTBEAT_ACTION,
                details={
                    "field": "action",
                    "expected": WsHeartbeatAction.PING,
                    "actual": heartbeat_payload.action,
                },
            )

        await websocket.send_json(
            build_pong_message().model_dump(mode="json")
        )
