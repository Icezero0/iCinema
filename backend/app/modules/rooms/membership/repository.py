from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rooms.models import RoomMember


class RoomMembershipRepository:
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

    async def get_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> RoomMember | None:
        result = await db.execute(
            select(RoomMember)
            .where(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
            )
            .options(selectinload(RoomMember.user))
        )
        return result.scalar_one_or_none()

    async def get_members_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
    ) -> list[RoomMember]:
        result = await db.execute(
            select(RoomMember)
            .where(RoomMember.room_id == room_id)
            .order_by(RoomMember.joined_at.asc(), RoomMember.user_id.asc())
            .options(selectinload(RoomMember.user))
        )
        return list(result.scalars().all())

    async def get_members_by_user_id(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[RoomMember]:
        result = await db.execute(
            select(RoomMember).where(RoomMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def delete_members_by_room_and_user_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> None:
        await db.execute(
            delete(RoomMember).where(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        await db.flush()

    async def update_member_role(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
        role: str,
    ) -> RoomMember | None:
        await db.execute(
            update(RoomMember)
            .where(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
            )
            .values(role=role)
        )
        await db.flush()
        return await self.get_member(db, room_id=room_id, user_id=user_id)
