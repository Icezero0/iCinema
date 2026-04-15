from __future__ import annotations

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.auth import authenticate_websocket_token
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsAuthPayload, build_ack_message


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

        await websocket.send_json(
            build_ack_message().model_dump(mode="json")
        )
        return connection