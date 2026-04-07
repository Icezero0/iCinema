from typing import Any

from app.modules.messages.schemas import MessageResponse
from app.realtime.channels import ChannelKey, room_channel, user_channel
from app.realtime.constants import WsEventType
from app.realtime.manager import RealtimeManager
from app.realtime.protocol import build_event_message
from app.realtime.state import (
    PlaybackState,
    PresenceState,
    RoomVideoSourceState,
    UserPlayerStatesState,
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
        exclude_connection_ids: set[str] | None = None,
    ) -> None:
        await self.manager.publish(
            channel=channel,
            message=build_event_message(
                event=event,
                data=data,
            ),
            exclude_connection_ids=exclude_connection_ids,
        )

    # =========================
    # signal events
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

    async def publish_presence(
        self,
        *,
        presence: PresenceState,
        exclude_connection_ids: set[str] | None = None,
    ) -> None:
        await self._publish_event(
            channel=room_channel(presence.room_id),
            event=WsEventType.PRESENCE,
            data=presence.model_dump(mode="json"),
            exclude_connection_ids=exclude_connection_ids,
        )

    async def publish_session(
        self,
        *,
        connection_id: str,
        room_id: int,
        reason: str,
    ) -> None:
        await self.manager.send_to_connection(
            connection_id=connection_id,
            message=build_event_message(
                event=WsEventType.SESSION,
                data={
                    "room_id": room_id,
                    "reason": reason,
                },
            ),
        )

    async def publish_room_video_source_set(
        self,
        *,
        room_video_source: RoomVideoSourceState,
    ) -> None:
        await self._publish_event(
            channel=room_channel(room_video_source.room_id),
            event=WsEventType.ROOM_VIDEO_SOURCE_SET,
            data=room_video_source.model_dump(mode="json"),
        )

    async def publish_playback_play(
        self,
        *,
        playback: PlaybackState,
    ) -> None:
        await self._publish_event(
            channel=room_channel(playback.room_id),
            event=WsEventType.PLAYBACK_PLAY,
            data=playback.model_dump(mode="json"),
        )

    async def publish_playback_pause(
        self,
        *,
        playback: PlaybackState,
    ) -> None:
        await self._publish_event(
            channel=room_channel(playback.room_id),
            event=WsEventType.PLAYBACK_PAUSE,
            data=playback.model_dump(mode="json"),
        )

    async def publish_playback_seek(
        self,
        *,
        playback: PlaybackState,
    ) -> None:
        await self._publish_event(
            channel=room_channel(playback.room_id),
            event=WsEventType.PLAYBACK_SEEK,
            data=playback.model_dump(mode="json"),
        )

    async def publish_user_player_states(
        self,
        *,
        user_player_states: UserPlayerStatesState,
    ) -> None:
        await self._publish_event(
            channel=room_channel(user_player_states.room_id),
            event=WsEventType.USER_PLAYER_STATES,
            data=user_player_states.model_dump(mode="json"),
        )
