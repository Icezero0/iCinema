from fastapi import APIRouter, WebSocket
from .handler import WebSocketHandler
from .manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点 - 支持Bearer token认证"""
    handler = WebSocketHandler()
    await handler.handle_connection(websocket)

@router.get("/ws/status")
async def websocket_status():
    """WebSocket连接状态"""
    try:
        return {
            "websocket_enabled": True,
            "online_users": manager.get_online_users_count(),
            "active_rooms": manager.get_active_rooms_count(),
            "endpoint": "/ws"
        }
    except ImportError:
        return {
            "websocket_enabled": False,
            "error": "WebSocket not available"
        }
