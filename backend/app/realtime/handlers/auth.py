from __future__ import annotations

import logging

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_extra
from app.realtime.auth import authenticate_websocket_token
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsAuthPayload, build_ack_message

logger = logging.getLogger("app.realtime")


class AuthHandler:
    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        websocket: WebSocket,
        connection: WsConnection | None,
        payload: dict,
    ) -> WsConnection:
        if connection is not None:
            await websocket.send_json(
                build_ack_message().model_dump(mode="json")
            )
            return connection

        auth_payload = WsAuthPayload.model_validate(payload)
        user = await authenticate_websocket_token(db, token=auth_payload.token)
        connection = await manager.register_connection(user_id=user.id, websocket=websocket)
        logger.info(
            "ws authenticated user_id=%s connection_id=%s",
            user.id,
            connection.connection_id,
            **log_extra(
                "ws.authenticated",
                user_id=user.id,
                connection_id=connection.connection_id,
            ),
        )

        await websocket.send_json(
            build_ack_message().model_dump(mode="json")
        )
        return connection
