from fastapi import FastAPI

from app.realtime.manager import RealtimeManager
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService


def setup_realtime(app: FastAPI) -> None:
    manager = RealtimeManager()
    room_presence_service = RoomPresenceService()
    room_video_runtime_service = RoomVideoRuntimeService()

    app.state.realtime_manager = manager
    app.state.realtime_publisher = RealtimePublisher(manager)
    app.state.realtime_room_presence_service = room_presence_service
    app.state.realtime_room_video_runtime_service = room_video_runtime_service