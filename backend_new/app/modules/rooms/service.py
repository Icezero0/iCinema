from sqlalchemy.ext.asyncio import AsyncSession

from math import ceil

from app.core.exceptions import ForbiddenError, NotFoundError, AppError
from app.modules.rooms.models import Room
from app.modules.rooms.repository import RoomRepository
from app.modules.rooms.schemas import RoomCreate, RoomPatch
from app.modules.users.models import User


class RoomService:
    def __init__(self) -> None:
        self.repo = RoomRepository()

    async def create_room(
        self,
        db: AsyncSession,
        *,
        user: User,
        payload: RoomCreate,
    ) -> Room:
        name = payload.name.strip()
        if not name:
            raise AppError(
                "Room name cannot be empty", code="invalid_room_name", status_code=400
            )

        room = await self.repo.create_room(
            db,
            name=name,
            owner_id=user.id,
            is_public=payload.is_public,
            config=payload.config,
        )

        await self.repo.create_member(
            db,
            room_id=room.id,
            user_id=user.id,
            role="owner",
        )

        await db.commit()
        return await self.get_room_by_id(db, user=user, room_id=room.id)

    async def get_rooms(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> dict:
        if name is not None:
            name = name.strip() or None

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

    async def get_room_by_id(
        self,
        db: AsyncSession,
        *,
        user: User,
        room_id: int,
    ) -> Room:
        room = await self.repo.get_room_by_id(db, room_id)
        if not room:
            raise NotFoundError("Room not found")

        if room.is_public or room.owner_id == user.id:
            return room

        member = await self.repo.get_member(db, room_id=room_id, user_id=user.id)
        if member:
            return room

        raise ForbiddenError("You do not have access to this room")

    async def get_owned_room_by_id(
        self,
        db: AsyncSession,
        *,
        user: User,
        room_id: int,
    ) -> Room:
        room = await self.get_room_by_id(db, user=user, room_id=room_id)
        if room.owner_id != user.id:
            raise ForbiddenError("Only the room owner can perform this action")
        return room

    async def patch_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        payload: RoomPatch,
    ) -> Room:
        room = await self.get_owned_room_by_id(db, room_id=room_id, user=user)
        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates and updates["name"] is not None:
            name = updates["name"].strip()
            if not name:
                raise AppError(
                    "Room name cannot be empty",
                    code="invalid_room_name",
                    status_code=400,
                )
            room.name = name

        if "is_public" in updates:
            room.is_public = updates["is_public"]

        if "config" in updates:
            room.config = updates["config"]

        room = await self.repo.save_room(db, room)
        await db.commit()
        return await self.get_room_by_id(db, user=user, room_id=room.id)

    async def delete_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        room = await self.get_owned_room_by_id(db, user=user, room_id=room_id)
        await self.repo.delete_room(db, room)
        await db.commit()
