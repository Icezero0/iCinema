from fastapi import FastAPI

from app.realtime.manager import RealtimeManager
from app.realtime.presence import RoomPresenceService
from app.realtime.publisher import RealtimePublisher


def setup_realtime(app: FastAPI) -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()

    app.state.realtime_manager = manager
    app.state.realtime_publisher = RealtimePublisher(manager)
    app.state.realtime_presence_service = presence_service