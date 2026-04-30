import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import log_extra
from app.modules.rooms.constants import RoomSyncPolicy
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.constants import AutoPlaybackAction
from app.realtime.handlers.dispatcher import RealtimeMessageHandler
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService

settings = get_settings()
logger = logging.getLogger("app.realtime")

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = getattr(ws, "client", None)
    logger.info(
        "ws connected client_ip=%s",
        client.host if client else None,
        **log_extra(
            "ws.connected",
            client_ip=client.host if client else None,
        ),
    )

    manager: RealtimeManager = ws.app.state.realtime_manager
    publisher: RealtimePublisher = ws.app.state.realtime_publisher
    presence_service: RoomPresenceService = ws.app.state.realtime_room_presence_service
    video_runtime_service: RoomVideoRuntimeService = (
        ws.app.state.realtime_room_video_runtime_service
    )

    room_settings_service = RoomSettingsService()
    handler = RealtimeMessageHandler(
        presence_service=presence_service,
        video_runtime_service=video_runtime_service,
    )
    connection: WsConnection | None = None
    auth_deadline = time.monotonic() + settings.ws_auth_timeout_seconds

    try:
        while True:
            if connection is None:
                remaining = auth_deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(
                        "ws auth timeout before auth message",
                        **log_extra("ws.auth_timeout"),
                    )
                    await ws.close(code=1008, reason="Authentication timeout")
                    break

                try:
                    raw_message = await asyncio.wait_for(
                        ws.receive_json(),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "ws auth timeout while waiting for auth message",
                        **log_extra("ws.auth_timeout"),
                    )
                    await ws.close(code=1008, reason="Authentication timeout")
                    break
            else:
                raw_message = await ws.receive_json()

            async with AsyncSessionLocal() as db:
                connection = await handler.handle(
                    db=db,
                    manager=manager,
                    publisher=publisher,
                    websocket=ws,
                    connection=connection,
                    raw_message=raw_message,
                )
    except WebSocketDisconnect:
        logger.info(
            "ws disconnected: user_id=%s connection_id=%s active_room_id=%s",
            connection.user_id if connection is not None else None,
            connection.connection_id if connection is not None else None,
            connection.active_room_id if connection is not None else None,
            **log_extra(
                "ws.disconnect",
                user_id=connection.user_id if connection is not None else "-",
                connection_id=connection.connection_id if connection is not None else None,
                active_room_id=connection.active_room_id if connection is not None else None,
            ),
        )
    except Exception:
        logger.exception(
            "ws unhandled exception: user_id=%s connection_id=%s active_room_id=%s",
            connection.user_id if connection is not None else None,
            connection.connection_id if connection is not None else None,
            connection.active_room_id if connection is not None else None,
            **log_extra(
                "ws.exception",
                user_id=connection.user_id if connection is not None else "-",
                connection_id=connection.connection_id if connection is not None else None,
                active_room_id=connection.active_room_id if connection is not None else None,
            ),
        )
        raise
    finally:
        if connection is not None:
            left_room_id = await presence_service.handle_disconnect(connection=connection)
            await manager.disconnect(connection.connection_id)

            if left_room_id is not None:
                async with AsyncSessionLocal() as db:
                    settings_obj = await room_settings_service.find_room_settings_by_room_id(
                        db,
                        room_id=left_room_id,
                    )
                    sync_policy = (
                        settings_obj.sync_policy
                        if settings_obj is not None
                        else RoomSyncPolicy.AUTO_SYNC
                    )

                presence = await presence_service.get_presence_state(room_id=left_room_id)
                session_exit_result = await video_runtime_service.handle_room_session_exit(
                    room_id=left_room_id,
                    user_id=connection.user_id,
                    sync_policy=sync_policy,
                    room_empty=not presence.present_user_ids,
                )
                if not session_exit_result.room_cleared and session_exit_result.user_resource_states is not None:
                    await publisher.publish_user_resource_states(
                        user_resource_states=session_exit_result.user_resource_states,
                    )
                    if (
                        session_exit_result.auto_action == AutoPlaybackAction.PLAY
                        and session_exit_result.auto_playback is not None
                    ):
                        await publisher.publish_playback_play(
                            playback=session_exit_result.auto_playback,
                        )

                logger.info(
                    "ws disconnect cleanup: user_id=%s connection_id=%s left_room_id=%s",
                    connection.user_id,
                    connection.connection_id,
                    left_room_id,
                    **log_extra(
                        "ws.disconnect_cleanup",
                        user_id=connection.user_id,
                        connection_id=connection.connection_id,
                        room_id=left_room_id,
                    ),
                )

                await publisher.publish_room_user_presence(
                    presence=presence,
                )
