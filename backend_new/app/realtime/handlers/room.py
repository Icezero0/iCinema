from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.service import RoomService
from app.realtime.constants import WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.presence import RoomPresenceService
from app.realtime.protocol import WsCommandPayload
from app.realtime.publisher import RealtimePublisher


class RoomCommandHandler:
    def __init__(self, presence_service: RoomPresenceService) -> None:
        self.room_service = RoomService()
        self.membership_service = RoomMembershipService()
        self.presence_service = presence_service

    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, Any] | None:
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
                manager=manager,
                publisher=publisher,
                connection=connection,
                command=command,
            )
            return None

        raise BadRequestError(f"Unsupported room command action: {command.action}")

    async def _handle_room_enter(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, Any]:
        room_id = self._extract_room_id(command)

        await self.room_service.get_room_by_id(db, room_id)
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=connection.user_id,
        )
        if role is None:
            raise ForbiddenError("You are not allowed to enter this room")

        previous_room_id = connection.active_room_id
        replaced_connection_id = await self.presence_service.find_room_user_connection(
            room_id=room_id,
            user_id=connection.user_id,
        )
        if replaced_connection_id == connection.connection_id:
            replaced_connection_id = None

        result = await self.presence_service.enter_room(
            manager=manager,
            connection=connection,
            room_id=room_id,
        )

        if replaced_connection_id is not None:
            await publisher.publish_session(
                connection_id=replaced_connection_id,
                room_id=room_id,
                reason="entered_elsewhere",
            )

        if previous_room_id is not None and previous_room_id != room_id:
            left_presence = await self.presence_service.get_presence_state(
                room_id=previous_room_id,
            )
            await publisher.publish_presence(
                presence=left_presence,
            )

        current_presence = await self.presence_service.get_presence_state(room_id=room_id)
        await publisher.publish_presence(
            presence=current_presence,
            exclude_connection_ids={connection.connection_id},
        )

        return result.snapshot.model_dump(mode="json")

    async def _handle_room_leave(
        self,
        *,
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
        await publisher.publish_presence(
            presence=presence,
            exclude_connection_ids={connection.connection_id},
        )

    @staticmethod
    def _extract_room_id(command: WsCommandPayload) -> int:
        if not command.data or "room_id" not in command.data:
            raise BadRequestError("room_id is required")

        room_id = command.data["room_id"]
        if not isinstance(room_id, int) or room_id <= 0:
            raise BadRequestError("room_id must be a positive integer")

        return room_id