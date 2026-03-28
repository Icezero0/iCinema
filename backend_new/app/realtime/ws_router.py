from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.realtime.handlers.dispatcher import RealtimeMessageHandler
from app.realtime.manager import RealtimeManager, WsConnection

router = APIRouter()
handler = RealtimeMessageHandler()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    manager: RealtimeManager = ws.app.state.realtime_manager
    connection: WsConnection | None = None

    try:
        while True:
            raw_message = await ws.receive_json()
            async with AsyncSessionLocal() as db:
                connection = await handler.handle(
                    db=db,
                    manager=manager,
                    websocket=ws,
                    connection=connection,
                    raw_message=raw_message,
                )
    except WebSocketDisconnect:
        pass
        # TODO: log the disconnect event
    finally:
        if connection is not None:
            await manager.disconnect(connection.connection_id)