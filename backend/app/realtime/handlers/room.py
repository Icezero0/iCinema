from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError, ForbiddenError
from app.core.logging import log_extra
from app.modules.rooms.constants import RoomSyncPolicy
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.service import RoomService
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.constants import AutoPlaybackAction, SessionCloseReason, WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService
from app.realtime.state import RoomSnapshot

logger = logging.getLogger("app.realtime")


class RoomCommandHandler:
    def __init__(
        self,
        presence_service: RoomPresenceService,
        video_runtime_service: RoomVideoRuntimeService,
    ) -> None:
        self.room_service = RoomService()
        self.room_settings_service = RoomSettingsService()
        self.membership_service = RoomMembershipService()
        self.presence_service = presence_service
        self.video_runtime_service = video_runtime_service

    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, object] | None:
        if command.action == WsCommandAction.ROOM_ENTER:
            return await self._handle_room_enter(
                db=db,
                manager=manager,
                publisher=publisher,
                connection=connection,
                command=command,
            )

        if command.action == WsCommandAction.ROOM_LEAVE:
            await self._handle_room_leave(
                db=db,
                manager=manager,
                publisher=publisher,
                connection=connection,
                command=command,
            )
            return None

        if command.action == WsCommandAction.ROOM_PRESENCE_GET:
            return await self._handle_room_presence_get(connection=connection)

        if command.action == WsCommandAction.ROOM_VIDEO_RUNTIME_GET:
            return await self._handle_room_video_runtime_get(connection=connection)

        raise BadRequestError(
            f"Unsupported room command action: {command.action}",
            reason=ErrorReason.UNSUPPORTED_ROOM_COMMAND_ACTION,
            details={"action": command.action},
        )

    async def _handle_room_presence_get(
        self,
        *,
        connection: WsConnection,
    ) -> dict[str, object]:
        room_id = self._require_active_room(connection)
        presence = await self.presence_service.get_presence_state(room_id=room_id)
        return {
            "presence": presence.model_dump(mode="json"),
        }

    async def _handle_room_video_runtime_get(
        self,
        *,
        connection: WsConnection,
    ) -> dict[str, object]:
        room_id = self._require_active_room(connection)
        room_video_source = await self.video_runtime_service.get_room_video_source(
            room_id=room_id,
        )
        playback = await self.video_runtime_service.get_playback(room_id=room_id)
        user_resource_states = await self.video_runtime_service.get_user_resource_states(
            room_id=room_id,
        )
        return {
            "room_video_source": (
                room_video_source.model_dump(mode="json")
                if room_video_source is not None
                else None
            ),
            "playback": playback.model_dump(mode="json") if playback is not None else None,
            "user_resource_states": user_resource_states.model_dump(mode="json"),
        }

    async def _handle_room_enter(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, object]:
        room_id = self._extract_room_id(command)

        await self.room_service.get_room_by_id(db, room_id)
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=connection.user_id,
        )
        if role is None:
            raise ForbiddenError(
                "You are not allowed to enter this room",
                reason=ErrorReason.ROOM_ENTER_FORBIDDEN,
                details={"room_id": room_id},
            )

        previous_room_id = connection.active_room_id
        replaced_connection_id = await self.presence_service.find_room_user_connection(
            room_id=room_id,
            user_id=connection.user_id,
        )
        if replaced_connection_id == connection.connection_id:
            replaced_connection_id = None

        current_presence = await self.presence_service.enter_room(
            manager=manager,
            connection=connection,
            room_id=room_id,
        )

        room_video_source = await self.video_runtime_service.get_room_video_source(
            room_id=room_id
        )
        playback = await self.video_runtime_service.get_playback(room_id=room_id)
        user_resource_states = await self.video_runtime_service.get_user_resource_states(
            room_id=room_id,
        )
        snapshot = RoomSnapshot(
            room_id=room_id,
            present_user_ids=current_presence.present_user_ids,
            room_video_source=room_video_source,
            playback=playback,
            user_resource_states=user_resource_states,
        )

        if replaced_connection_id is not None:
            await publisher.publish_session_closed(
                connection_id=replaced_connection_id,
                room_id=room_id,
                reason=SessionCloseReason.ENTERED_ELSEWHERE,
            )

        if previous_room_id is not None and previous_room_id != room_id:
            left_presence = await self.presence_service.get_presence_state(
                room_id=previous_room_id,
            )
            if not left_presence.present_user_ids:
                await self.video_runtime_service.clear_room_runtime(
                    room_id=previous_room_id,
                )
            else:
                sync_policy = await self._get_room_sync_policy(
                    db=db,
                    room_id=previous_room_id,
                )
                user_resource_states_update = await self.video_runtime_service.remove_user_resource_state(
                    room_id=previous_room_id,
                    user_id=connection.user_id,
                    sync_policy=sync_policy,
                )
                if user_resource_states_update is not None:
                    await publisher.publish_user_resource_states(
                        user_resource_states=user_resource_states_update.user_resource_states,
                    )
                    if (
                        user_resource_states_update.auto_action == AutoPlaybackAction.PLAY
                        and user_resource_states_update.auto_playback is not None
                    ):
                        await publisher.publish_playback_play(
                            playback=user_resource_states_update.auto_playback,
                        )

            await publisher.publish_room_user_presence(
                presence=left_presence,
            )

        await publisher.publish_room_user_presence(
            presence=current_presence,
            exclude_connection_ids={connection.connection_id},
        )
        logger.info(
            "ws room enter room_id=%s user_id=%s connection_id=%s previous_room_id=%s",
            room_id,
            connection.user_id,
            connection.connection_id,
            previous_room_id,
            **log_extra(
                "ws.room_enter",
                user_id=connection.user_id,
                connection_id=connection.connection_id,
                room_id=room_id,
                previous_room_id=previous_room_id,
            ),
        )

        return snapshot.model_dump(mode="json")

    async def _handle_room_leave(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> None:
        room_id = self._extract_room_id(command)

        left = await self.presence_service.leave_room(
            manager=manager,
            connection=connection,
            room_id=room_id,
        )
        if not left:
            return

        presence = await self.presence_service.get_presence_state(room_id=room_id)
        sync_policy = await self._get_room_sync_policy(db=db, room_id=room_id)
        session_exit_result = await self.video_runtime_service.handle_room_session_exit(
            room_id=room_id,
            user_id=connection.user_id,
            sync_policy=sync_policy,
            room_empty=not presence.present_user_ids,
        )
        if not session_exit_result.room_cleared and session_exit_result.user_resource_states is not None:
            await publisher.publish_user_resource_states(
                user_resource_states=session_exit_result.user_resource_states,
            )
            if (
                session_exit_result.auto_action == AutoPlaybackAction.PLAY
                and session_exit_result.auto_playback is not None
            ):
                await publisher.publish_playback_play(
                    playback=session_exit_result.auto_playback,
                )

        await publisher.publish_room_user_presence(
            presence=presence,
            exclude_connection_ids={connection.connection_id},
        )
        logger.info(
            "ws room leave room_id=%s user_id=%s connection_id=%s",
            room_id,
            connection.user_id,
            connection.connection_id,
            **log_extra(
                "ws.room_leave",
                user_id=connection.user_id,
                connection_id=connection.connection_id,
                room_id=room_id,
            ),
        )

    async def _get_room_sync_policy(
        self,
        *,
        db: AsyncSession,
        room_id: int,
    ) -> RoomSyncPolicy:
        settings = await self.room_settings_service.find_room_settings_by_room_id(
            db,
            room_id=room_id,
        )
        if settings is None:
            return RoomSyncPolicy.AUTO_SYNC
        return settings.sync_policy

    @staticmethod
    def _require_active_room(connection: WsConnection) -> int:
        room_id = connection.active_room_id
        if room_id is None:
            raise BadRequestError(
                "You must enter a room before querying room runtime",
                reason=ErrorReason.ROOM_NOT_ENTERED,
            )
        return room_id

    @staticmethod
    def _extract_room_id(command: WsCommandPayload) -> int:
        if not command.data or "room_id" not in command.data:
            raise BadRequestError(
                "room_id is required",
                reason=ErrorReason.MISSING_ROOM_ID,
                details={"field": "room_id", "constraint": "required"},
            )

        room_id = command.data["room_id"]
        if not isinstance(room_id, int) or room_id <= 0:
            raise BadRequestError(
                "room_id must be a positive integer",
                reason=ErrorReason.INVALID_ROOM_ID,
                details={"field": "room_id", "constraint": "positive_integer"},
            )

        return room_id
