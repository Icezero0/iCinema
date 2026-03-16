from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.rooms.constants import RoomPermission, RoomRole
from app.modules.rooms.models import Room, RoomMember
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.repository import RoomRepository
from app.modules.rooms.schemas import RoomCreate, RoomPatch
from app.modules.users.models import User


class RoomService:
    def __init__(self) -> None:
        self.repo = RoomRepository()

    async def find_room_by_id(self, db: AsyncSession, room_id: int) -> Room | None:
        return await self.repo.get_room_by_id(db, room_id)

    async def get_room_by_id(self, db: AsyncSession, room_id: int) -> Room:
        room = await self.find_room_by_id(db, room_id)
        if not room:
            raise NotFoundError("Room not found")
        return room

    async def find_room_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> RoomMember | None:
        return await self.repo.get_member(db, room_id=room_id, user_id=user_id)

    async def find_room_role(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> RoomRole | None:
        member = await self.find_room_member(db, room_id=room_id, user_id=user_id)
        if not member:
            return None

        try:
            return RoomRole(member.role)
        except ValueError:
            return None

    async def get_accessible_room_by_id(
        self,
        db: AsyncSession,
        *,
        user: User,
        room_id: int,
    ) -> Room:
        room = await self.get_room_by_id(db, room_id)

        if room.is_public:
            return room

        role = await self.find_room_role(db, room_id=room.id, user_id=user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.VIEW_ROOM)
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
            is_public=payload.is_public,
            config=payload.config,
        )

        await self.repo.create_member(
            db,
            room_id=room.id,
            user_id=user.id,
            role=RoomRole.OWNER.value,
        )

        await db.commit()
        await db.refresh(room)
        return room

    async def get_rooms(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> dict:
        items, total = await self.repo.get_rooms(
            db,
            user_id=user.id,
            page=page,
            page_size=page_size,
            name=name,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_room_members(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> dict:
        room = await self.get_room_by_id(db, room_id)

        role = await self.find_room_role(db, room_id=room.id, user_id=user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.VIEW_MEMBERS)

        items = await self.repo.get_members_by_room_id(db, room_id=room.id)
        return {
            "items": items,
            "total": len(items),
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
        role = await self.find_room_role(db, room_id=room.id, user_id=user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.UPDATE_ROOM)

        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates:
            room.name = updates["name"]

        if "is_public" in updates:
            room.is_public = updates["is_public"]

        if "config" in updates:
            room.config = updates["config"]

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
        role = await self.find_room_role(db, room_id=room.id, user_id=user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.DELETE_ROOM)

        await self.repo.delete_room(db, room)
        await db.commit()