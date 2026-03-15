from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rooms.models import Room, RoomMember


class RoomRepository:
    async def create_room(
        self,
        db: AsyncSession,
        *,
        name: str,
        owner_id: int,
        is_public: bool | None,
        config: str | None,
    ) -> Room:
        room = Room(
            name=name,
            owner_id=owner_id,
            is_public=is_public,
            config=config,
        )
        db.add(room)
        await db.flush()
        await db.refresh(room)
        return room

    async def create_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
        role: str,
    ) -> RoomMember:
        member = RoomMember(
            room_id=room_id,
            user_id=user_id,
            role=role,
        )
        db.add(member)
        await db.flush()
        await db.refresh(member)
        return member

    async def get_room_by_id(self, db: AsyncSession, room_id: int) -> Room | None:
        result = await db.execute(
            select(Room)
            .where(Room.id == room_id)
            .options(
                selectinload(Room.members).selectinload(RoomMember.user),
            )
        )
        return result.scalar_one_or_none()

    async def get_rooms(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> tuple[list[Room], int]:
        base_stmt = (
            select(Room)
            .distinct()
            .outerjoin(RoomMember, RoomMember.room_id == Room.id)
            .where(
                or_(
                    Room.is_public.is_(True),
                    Room.owner_id == user_id,
                    RoomMember.user_id == user_id,
                )
            )
        )

        if name:
            base_stmt = base_stmt.where(func.lower(Room.name).like(f"%{name.lower()}%"))

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            base_stmt
            .order_by(Room.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(Room.members).selectinload(RoomMember.user),
            )
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> RoomMember | None:
        result = await db.execute(
            select(RoomMember).where(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_room(self, db: AsyncSession, room: Room) -> Room:
        db.add(room)
        await db.flush()
        await db.refresh(room)
        return room

    async def delete_room(self, db: AsyncSession, room: Room) -> None:
        await db.delete(room)
        await db.flush()

    async def delete_members_by_room_id(self, db: AsyncSession, *, room_id: int) -> None:
        await db.execute(delete(RoomMember).where(RoomMember.room_id == room_id))
        await db.flush()