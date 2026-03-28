from fastapi import FastAPI

from app.realtime.manager import RealtimeManager
from app.realtime.publisher import RealtimePublisher


def setup_realtime(app: FastAPI) -> None:
    manager = RealtimeManager()
    app.state.realtime_manager = manager
    app.state.realtime_publisher = RealtimePublisher(manager)