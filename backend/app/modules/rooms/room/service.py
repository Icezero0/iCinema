from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.rooms.constants import RoomPermission, RoomRole, RoomVisibility
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.models import Room
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.room.repository import RoomRepository
from app.modules.rooms.room.schemas import RoomCreate, RoomPatch
from app.modules.rooms.settings.repository import RoomSettingsRepository
from app.modules.users.models import User


class RoomService:
    def __init__(self) -> None:
        self.repo = RoomRepository()
        self.membership_service = RoomMembershipService()
        self.settings_repo = RoomSettingsRepository()

    async def _require_room_permission(
        self,
        db: AsyncSession,
        *,
        room: Room,
        user: User,
        permission: RoomPermission,
    ) -> str:
        role = await self.membership_service.find_room_role(
            db,
            room_id=room.id,
            user_id=user.id,
        )
        if role is None:
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.ROOM_PERMISSION_DENIED,
                details={"room_id": room.id, "permission": permission},
            )

        require_room_permission(role, permission)
        return role

    async def find_room_by_id(self, db: AsyncSession, room_id: int) -> Room | None:
        return await self.repo.get_room_by_id(db, room_id)

    async def get_room_by_id(self, db: AsyncSession, room_id: int) -> Room:
        room = await self.find_room_by_id(db, room_id)
        if not room:
            raise NotFoundError(
                "Room not found",
                reason=ErrorReason.ROOM_NOT_FOUND,
                details={"room_id": room_id},
            )
        return room

    async def get_accessible_room_by_id(
        self,
        db: AsyncSession,
        *,
        user: User,
        room_id: int,
    ) -> Room:
        room = await self.get_room_by_id(db, room_id)

        if room.visibility == RoomVisibility.PUBLIC:
            return room

        await self._require_room_permission(
            db,
            room=room,
            user=user,
            permission=RoomPermission.VIEW_ROOM,
        )
        return room

    async def create_room(
        self,
        db: AsyncSession,
        *,
        user: User,
        payload: RoomCreate,
    ) -> Room:
        room = await self.repo.create_room(
            db,
            name=payload.name,
            owner_id=user.id,
            visibility=payload.visibility,
            join_audit_mode=payload.join_audit_mode,
        )

        await self.membership_service.repo.create_member(
            db,
            room_id=room.id,
            user_id=user.id,
            role=RoomRole.OWNER.value,
        )

        await self.settings_repo.create_settings(
            db,
            room_id=room.id,
        )

        await db.commit()
        await db.refresh(room)
        return room

    async def get_rooms(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        name: str | None = None,
        owner_username: str | None = None,
        owner_email: str | None = None,
    ) -> dict:
        items, total = await self.repo.get_rooms(
            db,
            page=page,
            page_size=page_size,
            name=name,
            owner_username=owner_username,
            owner_email=owner_email,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def patch_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        payload: RoomPatch,
    ) -> Room:
        room = await self.get_room_by_id(db, room_id)

        await self._require_room_permission(
            db,
            room=room,
            user=user,
            permission=RoomPermission.UPDATE_ROOM,
        )

        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates:
            room.name = updates["name"]

        if "visibility" in updates:
            room.visibility = updates["visibility"]

        if "join_audit_mode" in updates:
            room.join_audit_mode = updates["join_audit_mode"]

        room = await self.repo.save_room(db, room)
        await db.commit()
        await db.refresh(room)
        return room

    async def delete_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        room = await self.get_room_by_id(db, room_id)

        await self._require_room_permission(
            db,
            room=room,
            user=user,
            permission=RoomPermission.DELETE_ROOM,
        )

        await self.repo.delete_room(db, room)
        await db.commit()
