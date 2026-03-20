from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_json({"v": 1, "type": "auth.required", "payload": {"timeout": 30}})

    try:
        while True:
            data = await ws.receive_json()
            # 暂时先回显，后续换成 protocol + handlers
            await ws.send_json({"v": 1, "type": "echo", "payload": data})
    except WebSocketDisconnect:
        return