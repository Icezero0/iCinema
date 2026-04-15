from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import WebSocket

from app.realtime.channels import ChannelKey, user_channel
from app.realtime.protocol import WsMessage


@dataclass
class WsConnection:
    connection_id: str
    user_id: int
    websocket: WebSocket
    subscriptions: set[ChannelKey] = field(default_factory=set)
    active_room_id: int | None = None


class RealtimeManager:
    def __init__(self) -> None:
        self.connections: dict[str, WsConnection] = {}
        self.user_connections: dict[int, set[str]] = {}
        self.channel_connections: dict[ChannelKey, set[str]] = {}
        self._lock = asyncio.Lock()

    async def register_connection(
        self,
        *,
        user_id: int,
        websocket: WebSocket,
    ) -> WsConnection:
        connection = WsConnection(
            connection_id=uuid4().hex,
            user_id=user_id,
            websocket=websocket,
        )

        async with self._lock:
            self.connections[connection.connection_id] = connection
            self.user_connections.setdefault(user_id, set()).add(
                connection.connection_id
            )

            channel = user_channel(user_id)
            connection.subscriptions.add(channel)
            self.channel_connections.setdefault(channel, set()).add(
                connection.connection_id
            )

        return connection

    async def disconnect(self, connection_id: str) -> None:
        async with self._lock:
            connection = self.connections.pop(connection_id, None)
            if connection is None:
                return

            user_connection_ids = self.user_connections.get(connection.user_id)
            if user_connection_ids is not None:
                user_connection_ids.discard(connection_id)
                if not user_connection_ids:
                    self.user_connections.pop(connection.user_id, None)

            for channel in list(connection.subscriptions):
                connection_ids = self.channel_connections.get(channel)
                if connection_ids is not None:
                    connection_ids.discard(connection_id)
                    if not connection_ids:
                        self.channel_connections.pop(channel, None)

            connection.subscriptions.clear()

    async def subscribe(self, *, connection_id: str, channel: ChannelKey) -> None:
        async with self._lock:
            connection = self.connections.get(connection_id)
            if connection is None:
                return

            if channel in connection.subscriptions:
                return

            connection.subscriptions.add(channel)
            self.channel_connections.setdefault(channel, set()).add(connection_id)

    async def unsubscribe(self, *, connection_id: str, channel: ChannelKey) -> None:
        async with self._lock:
            connection = self.connections.get(connection_id)
            if connection is None:
                return

            if channel not in connection.subscriptions:
                return

            connection.subscriptions.discard(channel)

            connection_ids = self.channel_connections.get(channel)
            if connection_ids is not None:
                connection_ids.discard(connection_id)
                if not connection_ids:
                    self.channel_connections.pop(channel, None)

    async def send_to_connection(
        self,
        *,
        connection_id: str,
        message: WsMessage,
    ) -> None:
        connection = self.connections.get(connection_id)
        if connection is None:
            return

        try:
            await connection.websocket.send_json(message.model_dump(mode="json"))
        except Exception:  # noqa: BLE001
            try:
                await connection.websocket.close()
            except Exception:  # noqa: BLE001
                pass

            await self.disconnect(connection_id)

    async def publish(
        self,
        *,
        channel: ChannelKey,
        message: WsMessage,
        exclude_connection_ids: set[str] | None = None,
    ) -> None:
        excluded = exclude_connection_ids or set()
        connection_ids = list(self.channel_connections.get(channel, set()))

        for connection_id in connection_ids:
            if connection_id in excluded:
                continue
            await self.send_to_connection(connection_id=connection_id, message=message)