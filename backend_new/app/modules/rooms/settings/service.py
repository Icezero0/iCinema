from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.rooms.constants import RoomPermission
from app.modules.rooms.models import RoomSettings
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.room.service import RoomService
from app.modules.rooms.settings.repository import RoomSettingsRepository
from app.modules.rooms.settings.schemas import RoomSettingsPatch
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.users.models import User


class RoomSettingsService:
    def __init__(self) -> None:
        self.repo = RoomSettingsRepository()
        self.room_service = RoomService()
        self.membership_service = RoomMembershipService()

    async def _require_room_permission(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        permission: RoomPermission,
    ) -> str:
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, permission)
        return role

    async def find_room_settings_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
    ) -> RoomSettings | None:
        return await self.repo.get_by_room_id(db, room_id=room_id)

    async def get_room_settings_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
    ) -> RoomSettings:
        settings = await self.find_room_settings_by_room_id(db, room_id=room_id)
        if not settings:
            raise NotFoundError("Room settings not found")
        return settings

    async def create_default_settings(
        self,
        db: AsyncSession,
        *,
        room_id: int,
    ) -> RoomSettings:
        # internal composable helper: no commit here
        return await self.repo.create_settings(
            db,
            room_id=room_id,
        )

    async def get_accessible_room_settings_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> RoomSettings:
        await self.room_service.get_accessible_room_by_id(
            db,
            room_id=room_id,
            user=user,
        )

        settings = await self.find_room_settings_by_room_id(db, room_id=room_id)
        if settings:
            return settings

        # defensive fallback for legacy / partially migrated data
        settings = await self.create_default_settings(db, room_id=room_id)
        await db.commit()
        await db.refresh(settings)
        return settings

    async def patch_room_settings(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        payload: RoomSettingsPatch,
    ) -> RoomSettings:
        await self.room_service.get_room_by_id(db, room_id)

        await self._require_room_permission(
            db,
            room_id=room_id,
            user=user,
            permission=RoomPermission.UPDATE_ROOM,
        )

        settings = await self.find_room_settings_by_room_id(db, room_id=room_id)
        if not settings:
            settings = await self.create_default_settings(db, room_id=room_id)

        updates = payload.model_dump(exclude_unset=True)

        if "media_source_type" in updates:
            settings.media_source_type = updates["media_source_type"]

        if "sync_policy" in updates:
            settings.sync_policy = updates["sync_policy"]

        if "active_sync_permission" in updates:
            settings.active_sync_permission = updates["active_sync_permission"]

        settings = await self.repo.save_settings(db, settings)
        await db.commit()
        await db.refresh(settings)
        return settings