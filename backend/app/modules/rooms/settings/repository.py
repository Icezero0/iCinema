from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomVideoSourceType,
    RoomSyncPolicy,
)
from app.modules.rooms.models import RoomSettings


class RoomSettingsRepository:
    async def create_settings(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        selected_room_video_source_type: RoomVideoSourceType = (
            RoomVideoSourceType.EXTERNAL_URL
        ),
        sync_policy: RoomSyncPolicy = RoomSyncPolicy.AUTO_SYNC,
        active_sync_permission: RoomActiveSyncPermission = (
            RoomActiveSyncPermission.OWNER_AND_MANAGER
        ),
    ) -> RoomSettings:
        settings = RoomSettings(
            room_id=room_id,
            selected_room_video_source_type=selected_room_video_source_type,
            sync_policy=sync_policy,
            active_sync_permission=active_sync_permission,
        )
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
        return settings

    async def get_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
    ) -> RoomSettings | None:
        result = await db.execute(
            select(RoomSettings).where(RoomSettings.room_id == room_id)
        )
        return result.scalar_one_or_none()

    async def save_settings(
        self,
        db: AsyncSession,
        settings: RoomSettings,
    ) -> RoomSettings:
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
        return settings
