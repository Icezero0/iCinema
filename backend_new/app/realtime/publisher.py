from typing import Any

from app.modules.messages.schemas import MessageResponse
from app.realtime.constants import WsEventType
from app.realtime.manager import RealtimeManager
from app.realtime.protocol import (
    ChannelKey,
    build_event_message,
    room_channel,
    user_channel,
)


class RealtimePublisher:
    def __init__(self, manager: RealtimeManager) -> None:
        self.manager = manager

    # =========================
    # internal helper
    # =========================

    async def _publish_event(
        self,
        *,
        channel: ChannelKey,
        event: WsEventType,
        data: dict[str, Any] | None = None,
    ) -> None:
        await self.manager.publish(
            channel=channel,
            message=build_event_message(
                event=event,
                data=data,
            ),
        )

    # =========================
    # no data events
    # =========================

    async def publish_notification(
        self,
        *,
        user_id: int,
    ) -> None:
        await self._publish_event(
            channel=user_channel(user_id),
            event=WsEventType.NOTIFICATION,
            data=None,
        )

    async def publish_room_info(
        self,
        *,
        room_id: int,
    ) -> None:
        await self._publish_event(
            channel=room_channel(room_id),
            event=WsEventType.ROOM_INFO,
            data=None,
        )

    async def publish_room_settings(
        self,
        *,
        room_id: int,
    ) -> None:
        await self._publish_event(
            channel=room_channel(room_id),
            event=WsEventType.ROOM_SETTINGS,
            data=None,
        )

    async def publish_room_members(
        self,
        *,
        room_id: int,
    ) -> None:
        await self._publish_event(
            channel=room_channel(room_id),
            event=WsEventType.ROOM_MEMBERS,
            data=None,
        )

    # =========================
    # data events
    # =========================

    async def publish_message(
        self,
        *,
        room_id: int,
        message: MessageResponse,
    ) -> None:
        await self._publish_event(
            channel=room_channel(room_id),
            event=WsEventType.MESSAGE,
            data=message.model_dump(mode="json"),
        )

    async def publish_playback_play(
        self,
        *,
        room_id: int,
    ) -> None:
        pass

    async def publish_playback_pause(
        self,
        *,
        room_id: int,
    ) -> None:
        pass

    async def publish_playback_seek(
        self,
        *,
        room_id: int,
        position: float,
    ) -> None:
        pass

    async def publish_playback_source_set(
        self,
        *,
        room_id: int,
        source: str,
    ) -> None:
        pass
