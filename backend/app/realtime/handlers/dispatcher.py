from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import AppError, BadRequestError
from app.core.logging import log_extra
from app.realtime.constants import WsCommandAction, WsErrorCode, WsMessageType
from app.realtime.handlers.auth import AuthHandler
from app.realtime.handlers.heartbeat import HeartbeatHandler
from app.realtime.handlers.room import RoomCommandHandler
from app.realtime.handlers.room_video import RoomVideoCommandHandler
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import (
    WsCommandPayload,
    WsMessage,
    build_ack_message,
    build_error_message,
)
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService

logger = logging.getLogger("app.realtime")


class RealtimeMessageHandler:
    def __init__(
        self,
        *,
        presence_service: RoomPresenceService,
        video_runtime_service: RoomVideoRuntimeService,
    ) -> None:
        self.auth_handler = AuthHandler()
        self.heartbeat_handler = HeartbeatHandler()
        self.room_handler = RoomCommandHandler(
            presence_service=presence_service,
            video_runtime_service=video_runtime_service,
        )
        self.room_video_handler = RoomVideoCommandHandler(
            video_runtime_service=video_runtime_service,
        )

    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        websocket: WebSocket,
        connection: WsConnection | None,
        raw_message: dict,
    ) -> WsConnection | None:
        request_id = self._extract_request_id(raw_message)

        try:
            message = WsMessage.model_validate(raw_message)

            if message.type == WsMessageType.AUTH:
                return await self.auth_handler.handle(
                    db=db,
                    manager=manager,
                    websocket=websocket,
                    connection=connection,
                    payload=message.payload or {},
                )

            if message.type == WsMessageType.HEARTBEAT:
                await self.heartbeat_handler.handle(
                    websocket=websocket,
                    payload=message.payload,
                )
                return connection

            if message.type == WsMessageType.COMMAND:
                connection = self._require_authenticated(connection)
                command = WsCommandPayload.model_validate(message.payload or {})

                ack_data = await self._dispatch_command(
                    db=db,
                    manager=manager,
                    publisher=publisher,
                    connection=connection,
                    command=command,
                )

                await websocket.send_json(
                    build_ack_message(
                        request_id=command.request_id,
                        data=ack_data,
                    ).model_dump(mode="json")
                )
                return connection

            raise BadRequestError(
                f"Client cannot send message type: {message.type}",
                reason=ErrorReason.UNSUPPORTED_CLIENT_MESSAGE_TYPE,
                details={"type": message.type},
            )

        except AppError as e:
            logger.warning(
                "ws app error connection_id=%s user_id=%s request_id=%s code=%s",
                connection.connection_id if connection is not None else None,
                connection.user_id if connection is not None else None,
                request_id,
                e.code,
                **log_extra(
                    "ws.app_error",
                    user_id=connection.user_id if connection is not None else "-",
                    connection_id=connection.connection_id if connection is not None else None,
                    request_id=request_id,
                    error_code=e.code,
                ),
            )
            await websocket.send_json(
                build_error_message(
                    code=e.code,
                    request_id=request_id,
                    reason=e.reason,
                    message=e.message,
                    details=e.details,
                ).model_dump(mode="json"),
            )
            return connection

        except ValidationError as e:
            details = {
                "errors": e.errors(include_url=False, include_input=False),
            }
            logger.warning(
                "ws invalid payload connection_id=%s user_id=%s request_id=%s",
                connection.connection_id if connection is not None else None,
                connection.user_id if connection is not None else None,
                request_id,
                **log_extra(
                    "ws.invalid_payload",
                    user_id=connection.user_id if connection is not None else "-",
                    connection_id=connection.connection_id if connection is not None else None,
                    request_id=request_id,
                    error_code=WsErrorCode.INVALID_PAYLOAD,
                    error_reason=ErrorReason.INVALID_WEBSOCKET_PAYLOAD,
                ),
            )
            await websocket.send_json(
                build_error_message(
                    code=WsErrorCode.INVALID_PAYLOAD,
                    request_id=request_id,
                    reason=ErrorReason.INVALID_WEBSOCKET_PAYLOAD,
                    message="Invalid websocket payload",
                    details=details,
                ).model_dump(mode="json"),
            )
            return connection

    async def _dispatch_command(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, Any] | None:
        if command.action in {
            WsCommandAction.ROOM_ENTER,
            WsCommandAction.ROOM_LEAVE,
            WsCommandAction.ROOM_PRESENCE_GET,
            WsCommandAction.ROOM_VIDEO_RUNTIME_GET,
        }:
            return await self.room_handler.handle(
                db=db,
                manager=manager,
                publisher=publisher,
                connection=connection,
                command=command,
            )

        if command.action in {
            WsCommandAction.PLAYBACK_PAUSE,
            WsCommandAction.PLAYBACK_PLAY,
            WsCommandAction.PLAYBACK_SEEK,
            WsCommandAction.ROOM_VIDEO_SOURCE_SET,
            WsCommandAction.USER_RESOURCE_STATUS,
        }:
            return await self.room_video_handler.handle(
                db=db,
                manager=manager,
                publisher=publisher,
                connection=connection,
                command=command,
            )

        raise BadRequestError(
            f"Unsupported command action: {command.action}",
            reason=ErrorReason.UNSUPPORTED_COMMAND_ACTION,
            details={"action": command.action},
        )

    @staticmethod
    def _extract_request_id(raw_message: dict) -> str | None:
        if not isinstance(raw_message, dict):
            return None

        payload = raw_message.get("payload")
        if not isinstance(payload, dict):
            return None

        request_id = payload.get("request_id")
        if isinstance(request_id, str):
            return request_id
        return None

    @staticmethod
    def _require_authenticated(connection: WsConnection | None) -> WsConnection:
        if connection is None:
            raise BadRequestError(
                "Authentication required before this action",
                reason=ErrorReason.AUTHENTICATION_REQUIRED,
            )
        return connection
