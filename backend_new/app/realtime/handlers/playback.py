from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.realtime.constants import WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.publisher import RealtimePublisher


class PlaybackCommandHandler:
    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, Any] | None:
        if command.action in {
            WsCommandAction.PLAYBACK_PAUSE,
            WsCommandAction.PLAYBACK_PLAY,
            WsCommandAction.PLAYBACK_SEEK,
            WsCommandAction.PLAYBACK_SOURCE_SET,
        }:
            raise BadRequestError(f"Playback command not implemented yet: {command.action}")

        raise BadRequestError(f"Unsupported playback command action: {command.action}")