from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.service import RoomService
from app.realtime.constants import WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload, room_channel


class RoomCommandHandler:
    def __init__(self) -> None:
        self.room_service = RoomService()
        self.membership_service = RoomMembershipService()

    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> None:
        if command.action == WsCommandAction.ROOM_ENTER:
            await self._handle_room_enter(
                db=db,
                manager=manager,
                connection=connection,
                command=command,
            )
            return

        if command.action == WsCommandAction.ROOM_LEAVE:
            await self._handle_room_leave(
                manager=manager,
                connection=connection,
                command=command,
            )
            return

        raise BadRequestError(f"Unsupported room command action: {command.action}")

    async def _handle_room_enter(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> None:
        room_id = self._extract_room_id(command)

        await self.room_service.get_room_by_id(db, room_id)
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=connection.user_id,
        )
        if role is None:
            raise ForbiddenError("You are not allowed to enter this room channel")

        await manager.subscribe(
            connection_id=connection.connection_id,
            channel=room_channel(room_id),
        )

    async def _handle_room_leave(
        self,
        *,
        manager: RealtimeManager,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> None:
        room_id = self._extract_room_id(command)

        await manager.unsubscribe(
            connection_id=connection.connection_id,
            channel=room_channel(room_id),
        )

    @staticmethod
    def _extract_room_id(command: WsCommandPayload) -> int:
        if not command.data or "room_id" not in command.data:
            raise BadRequestError("room_id is required")

        room_id = command.data["room_id"]
        if not isinstance(room_id, int) or room_id <= 0:
            raise BadRequestError("room_id must be a positive integer")

        return room_id