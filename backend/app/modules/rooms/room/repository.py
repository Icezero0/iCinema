from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.orm import selectinload

from app.modules.rooms.constants import RoomJoinAuditMode, RoomRole, RoomVisibility
from app.modules.rooms.models import Room, RoomMember
from app.modules.users.models import User


class RoomRepository:
    async def create_room(
        self,
        db: AsyncSession,
        *,
        name: str,
        owner_id: int,
        visibility: RoomVisibility,
        join_audit_mode: RoomJoinAuditMode,
    ) -> Room:
        room = Room(
            name=name,
            owner_id=owner_id,
            visibility=visibility,
            join_audit_mode=join_audit_mode,
        )
        db.add(room)
        await db.flush()
        await db.refresh(room)
        return room

    async def get_room_by_id(self, db: AsyncSession, room_id: int) -> Room | None:
        result = await db.execute(
            select(Room)
            .options(selectinload(Room.settings))
            .where(Room.id == room_id)
        )
        return result.scalar_one_or_none()

    async def get_rooms(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        name: str | None = None,
        owner_username: str | None = None,
        owner_email: str | None = None,
    ) -> tuple[list[Room], int]:
        owner = aliased(User)

        base_stmt = (
            select(Room)
            .join(owner, Room.owner_id == owner.id)
            .where(Room.visibility == RoomVisibility.PUBLIC)
        )

        if name:
            base_stmt = base_stmt.where(func.lower(Room.name).like(f"%{name.lower()}%"))
        if owner_username:
            base_stmt = base_stmt.where(
                func.lower(owner.username).like(f"%{owner_username.lower()}%")
            )
        if owner_email:
            base_stmt = base_stmt.where(
                func.lower(owner.email).like(f"%{owner_email.lower()}%")
            )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            base_stmt.options(selectinload(Room.settings), selectinload(Room.owner))
            .order_by(Room.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_user_rooms(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        page: int,
        page_size: int,
        role: RoomRole | None = None,
    ) -> tuple[list[tuple[Room, RoomRole]], int]:
        membership = aliased(RoomMember)

        base_stmt = (
            select(Room, membership.role.label("member_role"))
            .outerjoin(
                membership,
                and_(
                    membership.room_id == Room.id,
                    membership.user_id == user_id,
                ),
            )
            .where(
                or_(
                    Room.owner_id == user_id,
                    membership.user_id == user_id,
                )
            )
        )

        if role is not None:
            if role == RoomRole.OWNER:
                base_stmt = base_stmt.where(Room.owner_id == user_id)
            else:
                base_stmt = base_stmt.where(membership.role == role.value)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            base_stmt.options(selectinload(Room.owner))
            .order_by(Room.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items: list[tuple[Room, RoomRole]] = []
        for room, member_role in result.all():
            resolved_role = RoomRole.OWNER if room.owner_id == user_id else RoomRole(member_role)
            items.append((room, resolved_role))

        return items, total

    async def save_room(self, db: AsyncSession, room: Room) -> Room:
        db.add(room)
        await db.flush()
        await db.refresh(room)
        return room

    async def delete_room(self, db: AsyncSession, room: Room) -> None:
        await db.delete(room)
        await db.flush()
