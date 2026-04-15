from __future__ import annotations

import asyncio

from app.realtime.channels import room_channel
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.state import PresenceState


class RoomPresenceService:
    def __init__(self) -> None:
        self.room_user_connections: dict[int, dict[int, str]] = {}
        self._lock = asyncio.Lock()

    async def find_room_user_connection(
        self,
        *,
        room_id: int,
        user_id: int,
    ) -> str | None:
        async with self._lock:
            room_connections = self.room_user_connections.get(room_id, {})
            return room_connections.get(user_id)

    async def enter_room(
        self,
        *,
        manager: RealtimeManager,
        connection: WsConnection,
        room_id: int,
    ) -> PresenceState:
        async with self._lock:
            current_room_id = connection.active_room_id
            if current_room_id == room_id:
                room_connections = self.room_user_connections.get(room_id, {})
                if room_connections.get(connection.user_id) == connection.connection_id:
                    return self._build_presence_state_locked(room_id)

            if current_room_id is not None and current_room_id != room_id:
                await self._leave_room_locked(
                    manager=manager,
                    connection=connection,
                    room_id=current_room_id,
                )

            room_connections = self.room_user_connections.setdefault(room_id, {})
            existing_connection_id = room_connections.get(connection.user_id)

            if (
                existing_connection_id is not None
                and existing_connection_id != connection.connection_id
            ):
                old_connection = manager.connections.get(existing_connection_id)

                room_connections.pop(connection.user_id, None)

                if old_connection is not None:
                    old_connection.active_room_id = None
                    await manager.unsubscribe(
                        connection_id=existing_connection_id,
                        channel=room_channel(room_id),
                    )

            room_connections = self.room_user_connections.setdefault(room_id, {})
            room_connections[connection.user_id] = connection.connection_id
            connection.active_room_id = room_id

            await manager.subscribe(
                connection_id=connection.connection_id,
                channel=room_channel(room_id),
            )

            return self._build_presence_state_locked(room_id)

    async def leave_room(
        self,
        *,
        manager: RealtimeManager,
        connection: WsConnection,
        room_id: int,
    ) -> bool:
        async with self._lock:
            current_room_id = connection.active_room_id
            if current_room_id != room_id:
                return False

            await self._leave_room_locked(
                manager=manager,
                connection=connection,
                room_id=room_id,
            )
            return True

    async def handle_disconnect(
        self,
        *,
        connection: WsConnection,
    ) -> int | None:
        async with self._lock:
            room_id = connection.active_room_id
            if room_id is None:
                return None

            room_connections = self.room_user_connections.get(room_id)
            if room_connections is not None:
                current_connection_id = room_connections.get(connection.user_id)
                if current_connection_id == connection.connection_id:
                    room_connections.pop(connection.user_id, None)
                    if not room_connections:
                        self.room_user_connections.pop(room_id, None)

            connection.active_room_id = None
            return room_id

    async def get_presence_state(
        self,
        *,
        room_id: int,
    ) -> PresenceState:
        async with self._lock:
            return self._build_presence_state_locked(room_id)

    async def evict_room_user(
        self,
        *,
        manager: RealtimeManager,
        room_id: int,
        user_id: int,
    ) -> str | None:
        async with self._lock:
            room_connections = self.room_user_connections.get(room_id)
            if room_connections is None:
                return None

            connection_id = room_connections.get(user_id)
            if connection_id is None:
                return None

            connection = manager.connections.get(connection_id)
            if connection is not None:
                await self._leave_room_locked(
                    manager=manager,
                    connection=connection,
                    room_id=room_id,
                )
            else:
                room_connections.pop(user_id, None)
                if not room_connections:
                    self.room_user_connections.pop(room_id, None)

            return connection_id

    async def evict_room_users(
        self,
        *,
        manager: RealtimeManager,
        room_id: int,
    ) -> list[tuple[int, str]]:
        async with self._lock:
            room_connections = self.room_user_connections.get(room_id)
            if room_connections is None:
                return []

            targets = list(room_connections.items())
            evicted: list[tuple[int, str]] = []

            for user_id, connection_id in targets:
                connection = manager.connections.get(connection_id)
                if connection is not None:
                    await self._leave_room_locked(
                        manager=manager,
                        connection=connection,
                        room_id=room_id,
                    )
                else:
                    room_connections.pop(user_id, None)
                    if not room_connections:
                        self.room_user_connections.pop(room_id, None)
                        room_connections = None
                evicted.append((user_id, connection_id))

            return evicted

    async def _leave_room_locked(
        self,
        *,
        manager: RealtimeManager,
        connection: WsConnection,
        room_id: int,
    ) -> None:
        room_connections = self.room_user_connections.get(room_id)
        if room_connections is not None:
            current_connection_id = room_connections.get(connection.user_id)
            if current_connection_id == connection.connection_id:
                room_connections.pop(connection.user_id, None)
                if not room_connections:
                    self.room_user_connections.pop(room_id, None)

        connection.active_room_id = None

        await manager.unsubscribe(
            connection_id=connection.connection_id,
            channel=room_channel(room_id),
        )

    def _build_presence_state_locked(self, room_id: int) -> PresenceState:
        room_connections = self.room_user_connections.get(room_id, {})
        return PresenceState(
            room_id=room_id,
            present_user_ids=sorted(room_connections.keys()),
        )
