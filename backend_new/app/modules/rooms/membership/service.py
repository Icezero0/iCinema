from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.modules.rooms.constants import RoomPermission, RoomRole
from app.modules.rooms.models import RoomMember
from app.modules.rooms.membership.repository import RoomMembershipRepository
from app.modules.rooms.permissions import require_room_permission
from app.modules.users.models import User


class RoomMembershipService:
    def __init__(self) -> None:
        self.repo = RoomMembershipRepository()

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
        if member is None:
            return None

        try:
            return RoomRole(member.role)
        except ValueError:
            return None

    async def get_room_members(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> dict[str, list[RoomMember] | int]:
        role = await self.find_room_role(db, room_id=room_id, user_id=user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.VIEW_MEMBERS)

        items = await self.repo.get_members_by_room_id(db, room_id=room_id)
        return {
            "items": items,
            "total": len(items),
        }

    async def add_room_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
        role: RoomRole = RoomRole.MEMBER,
    ) -> RoomMember:
        return await self.repo.create_member(
            db,
            room_id=room_id,
            user_id=user_id,
            role=role,
        )

    async def remove_room_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        target_user_id: int,
        current_user: User,
    ) -> None:
        target_member = await self.find_room_member(
            db,
            room_id=room_id,
            user_id=target_user_id,
        )
        if target_member is None:
            raise NotFoundError("Room member not found")

        role = await self.find_room_role(db, room_id=room_id, user_id=current_user.id)
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        if current_user.id == target_user_id:
            raise ForbiddenError("You cannot remove yourself from the room")

        try:
            target_role = RoomRole(target_member.role)
        except ValueError:
            raise BadRequestError("Invalid target member role")

        if target_role == RoomRole.OWNER:
            raise ForbiddenError("Owner cannot be removed from the room")

        if target_role == RoomRole.MANAGER:
            require_room_permission(role, RoomPermission.MANAGE_MANAGERS)

        elif target_role == RoomRole.MEMBER:
            require_room_permission(role, RoomPermission.MANAGE_MEMBERS)

        else:
            raise BadRequestError("Invalid target member role")

        await self.repo.delete_members_by_room_and_user_id(
            db,
            room_id=room_id,
            user_id=target_user_id,
        )
