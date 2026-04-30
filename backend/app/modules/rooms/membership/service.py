from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.modules.rooms.constants import RoomPermission, RoomRole
from app.modules.rooms.models import RoomMember
from app.modules.rooms.membership.repository import RoomMembershipRepository
from app.modules.rooms.permissions import require_room_permission, has_room_permission
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
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.ROOM_PERMISSION_DENIED,
                details={"room_id": room_id, "permission": RoomPermission.VIEW_MEMBERS},
            )

        require_room_permission(role, RoomPermission.VIEW_MEMBERS)

        items = await self.repo.get_members_by_room_id(db, room_id=room_id)
        return {
            "items": items,
            "total": len(items),
        }

    async def add_room_member_in_tx(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
        role: RoomRole = RoomRole.MEMBER,
    ) -> RoomMember:
        # This helper participates in the caller's transaction and does not commit.
        return await self.repo.create_member(
            db,
            room_id=room_id,
            user_id=user_id,
            role=role,
        )
    
    async def get_room_user_ids_by_permission(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        permission: RoomPermission,
    ) -> list[int]:
        members = await self.repo.get_members_by_room_id(db, room_id=room_id)
        user_ids = []
        for member in members:
            try:
                role = RoomRole(member.role)
            except ValueError:
                continue

            if has_room_permission(role=role, permission=permission):
                user_ids.append(member.user_id)

        return user_ids

    async def get_room_ids_by_permission(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        permission: RoomPermission,
    ) -> list[int]:
        members = await self.repo.get_members_by_user_id(db, user_id=user_id)
        room_ids: list[int] = []

        for member in members:
            try:
                role = RoomRole(member.role)
            except ValueError:
                continue

            if has_room_permission(role=role, permission=permission):
                room_ids.append(member.room_id)

        return room_ids

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
            raise NotFoundError(
                "Room member not found",
                reason=ErrorReason.ROOM_MEMBER_NOT_FOUND,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        role = await self.find_room_role(db, room_id=room_id, user_id=current_user.id)
        if role is None:
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.ROOM_PERMISSION_DENIED,
                details={"room_id": room_id, "permission": RoomPermission.MANAGE_MEMBERS},
            )

        if current_user.id == target_user_id:
            raise ForbiddenError(
                "You cannot remove yourself from the room",
                reason=ErrorReason.CANNOT_REMOVE_SELF_FROM_ROOM,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        try:
            target_role = RoomRole(target_member.role)
        except ValueError:
            raise BadRequestError(
                "Invalid target member role",
                reason=ErrorReason.INVALID_ROOM_MEMBER_ROLE,
                details={
                    "room_id": room_id,
                    "user_id": target_user_id,
                    "role": target_member.role,
                },
            )

        if target_role == RoomRole.OWNER:
            raise ForbiddenError(
                "Owner cannot be removed from the room",
                reason=ErrorReason.OWNER_CANNOT_BE_REMOVED_FROM_ROOM,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        if target_role == RoomRole.MANAGER:
            require_room_permission(role, RoomPermission.MANAGE_MANAGERS)

        elif target_role == RoomRole.MEMBER:
            require_room_permission(role, RoomPermission.MANAGE_MEMBERS)

        else:
            raise BadRequestError(
                "Invalid target member role",
                reason=ErrorReason.INVALID_ROOM_MEMBER_ROLE,
                details={
                    "room_id": room_id,
                    "user_id": target_user_id,
                    "role": target_role,
                },
            )

        await self.repo.delete_members_by_room_and_user_id(
            db,
            room_id=room_id,
            user_id=target_user_id,
        )
        await db.commit()

    async def leave_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        member = await self.find_room_member(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        if member is None:
            raise NotFoundError(
                "Room member not found",
                reason=ErrorReason.ROOM_MEMBER_NOT_FOUND,
                details={"room_id": room_id, "user_id": user.id},
            )

        try:
            role = RoomRole(member.role)
        except ValueError:
            raise BadRequestError(
                "Invalid member role",
                reason=ErrorReason.INVALID_ROOM_MEMBER_ROLE,
                details={"room_id": room_id, "user_id": user.id, "role": member.role},
            )

        if role == RoomRole.OWNER:
            raise ForbiddenError(
                "Owner cannot leave the room",
                reason=ErrorReason.OWNER_CANNOT_LEAVE_ROOM,
                details={"room_id": room_id, "user_id": user.id},
            )

        await self.repo.delete_members_by_room_and_user_id(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        await db.commit()

    async def set_room_member_manager_status(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        target_user_id: int,
        is_manager: bool,
        current_user: User,
    ) -> RoomMember:
        role = await self.find_room_role(db, room_id=room_id, user_id=current_user.id)
        if role is None:
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.ROOM_PERMISSION_DENIED,
                details={"room_id": room_id, "permission": RoomPermission.MANAGE_MANAGERS},
            )

        require_room_permission(role, RoomPermission.MANAGE_MANAGERS)

        target_member = await self.find_room_member(
            db,
            room_id=room_id,
            user_id=target_user_id,
        )
        if target_member is None:
            raise NotFoundError(
                "Room member not found",
                reason=ErrorReason.ROOM_MEMBER_NOT_FOUND,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        try:
            target_role = RoomRole(target_member.role)
        except ValueError:
            raise BadRequestError(
                "Invalid target member role",
                reason=ErrorReason.INVALID_ROOM_MEMBER_ROLE,
                details={
                    "room_id": room_id,
                    "user_id": target_user_id,
                    "role": target_member.role,
                },
            )

        if target_role == RoomRole.OWNER:
            raise ForbiddenError(
                "Owner role cannot be changed",
                reason=ErrorReason.OWNER_ROLE_CANNOT_BE_CHANGED,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        next_role = RoomRole.MANAGER if is_manager else RoomRole.MEMBER
        if target_role == next_role:
            return target_member

        updated_member = await self.repo.update_member_role(
            db,
            room_id=room_id,
            user_id=target_user_id,
            role=next_role.value,
        )
        if updated_member is None:
            raise NotFoundError(
                "Room member not found",
                reason=ErrorReason.ROOM_MEMBER_NOT_FOUND,
                details={"room_id": room_id, "user_id": target_user_id},
            )

        await db.commit()
        return updated_member
