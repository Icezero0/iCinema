from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.realtime.constants import WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload


class PlaybackCommandHandler:
    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> None:
        if command.action in {
            WsCommandAction.PLAYBACK_PAUSE,
            WsCommandAction.PLAYBACK_PLAY,
            WsCommandAction.PLAYBACK_SEEK,
            WsCommandAction.PLAYBACK_SET_SOURCE,
        }:
            raise BadRequestError(f"Playback command not implemented yet: {command.action}")

        raise BadRequestError(f"Unsupported playback command action: {command.action}")