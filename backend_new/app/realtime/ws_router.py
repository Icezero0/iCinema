import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.realtime.handlers.dispatcher import RealtimeMessageHandler
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService

settings = get_settings()

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    manager: RealtimeManager = ws.app.state.realtime_manager
    publisher: RealtimePublisher = ws.app.state.realtime_publisher
    presence_service: RoomPresenceService = ws.app.state.realtime_room_presence_service
    video_runtime_service: RoomVideoRuntimeService = (
        ws.app.state.realtime_room_video_runtime_service
    )

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
                    await ws.close(code=1008, reason="Authentication timeout")
                    break

                try:
                    raw_message = await asyncio.wait_for(
                        ws.receive_json(),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
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
        pass
        # TODO: log the disconnect event
    finally:
        if connection is not None:
            left_room_id = await presence_service.handle_disconnect(connection=connection)
            await manager.disconnect(connection.connection_id)

            if left_room_id is not None:
                presence = await presence_service.get_presence_state(room_id=left_room_id)
                if not presence.present_user_ids:
                    await video_runtime_service.clear_room_runtime(room_id=left_room_id)

                await publisher.publish_presence(
                    presence=presence,
                )