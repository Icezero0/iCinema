from types import SimpleNamespace

from fastapi import FastAPI

from app.realtime.bootstrap import setup_realtime
from app.realtime.manager import RealtimeManager
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService


# setup_realtime 会把 realtime 运行时组件挂到 FastAPI app.state 上
def test_setup_realtime_registers_runtime_services_on_app_state() -> None:
    app = FastAPI()
    app.state = SimpleNamespace()

    setup_realtime(app)

    assert isinstance(app.state.realtime_manager, RealtimeManager)
    assert isinstance(app.state.realtime_publisher, RealtimePublisher)
    assert isinstance(app.state.realtime_room_presence_service, RoomPresenceService)
    assert isinstance(
        app.state.realtime_room_video_runtime_service,
        RoomVideoRuntimeService,
    )
