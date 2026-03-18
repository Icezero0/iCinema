from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.modules.rooms.constants import (
    RoomRole,
    RoomJoinRequestAction,
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomPermission,
)
from app.modules.rooms.join_request.repository import RoomJoinRequestRepository
from app.modules.rooms.models import RoomJoinRequest
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.room.service import RoomService
from app.modules.users.models import User
from app.modules.users.service import UserService


class RoomJoinRequestService:
    def __init__(self) -> None:
        self.repo = RoomJoinRequestRepository()
        self.membership_service = RoomMembershipService()
        self.room_service = RoomService()
        self.user_service = UserService()

    # =========================
    # create
    # =========================

    async def create_apply_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> RoomJoinRequest:
        await self.room_service.get_room_by_id(db, room_id)
        await self._ensure_user_not_member(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        await self._ensure_no_pending_request(
            db,
            room_id=room_id,
            target_user_id=user.id,
        )

        request = await self.repo.create_request(
            db,
            room_id=room_id,
            initiator_user_id=user.id,
            target_user_id=user.id,
            source=RoomJoinRequestSource.APPLY,
            status=RoomJoinRequestStatus.PENDING,
            room_action=RoomJoinRequestAction.PENDING,
            target_action=RoomJoinRequestAction.APPROVED,
        )

        # TODO: notify room side
        await db.commit()
        await db.refresh(request)
        return request

    async def create_invite_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        target_user_id: int,
        user: User,
    ) -> RoomJoinRequest:
        await self.room_service.get_room_by_id(db, room_id)
        await self.user_service.get_user_by_id(db, target_user_id)

        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.INVITE_USER)

        await self._ensure_user_not_member(
            db,
            room_id=room_id,
            user_id=target_user_id,
        )
        await self._ensure_no_pending_request(
            db,
            room_id=room_id,
            target_user_id=target_user_id,
        )

        room_action = RoomJoinRequestAction.PENDING
        source = RoomJoinRequestSource.MEMBER_INVITE
        room_action_by_user_id = None

        try:
            require_room_permission(role, RoomPermission.REVIEW_JOIN_REQUEST)
            room_action = RoomJoinRequestAction.APPROVED
            source = RoomJoinRequestSource.INVITE
            room_action_by_user_id = user.id
        except ForbiddenError:
            pass

        request = await self.repo.create_request(
            db,
            room_id=room_id,
            initiator_user_id=user.id,
            target_user_id=target_user_id,
            source=source,
            status=RoomJoinRequestStatus.PENDING,
            room_action=room_action,
            target_action=RoomJoinRequestAction.PENDING,
            room_action_by_user_id=room_action_by_user_id,
        )

        await db.commit()
        await db.refresh(request)
        return request

    # =========================
    # get
    # =========================

    async def find_join_request_by_id(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> RoomJoinRequest | None:
        return await self.repo.get_request_by_id(db, request_id)

    async def get_join_request_by_id(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> RoomJoinRequest:
        request = await self.find_join_request_by_id(db, request_id)
        if not request:
            raise NotFoundError("Join request not found.")
        return request

    async def get_accessible_join_request_by_id(
        self,
        db: AsyncSession,
        *,
        request_id: int,
        user: User,
    ) -> RoomJoinRequest:
        request = await self.get_join_request_by_id(db, request_id)

        if user.id in {request.initiator_user_id, request.target_user_id}:
            return request

        await self._ensure_can_review_by_room(
            db,
            room_id=request.room_id,
            user=user,
        )
        return request

    async def get_room_join_requests(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        page: int,
        page_size: int,
        status: RoomJoinRequestStatus | None = None,
        source: RoomJoinRequestSource | None = None,
    ) -> dict:
        await self.room_service.get_room_by_id(db, room_id)
        await self._ensure_can_review_by_room(
            db,
            room_id=room_id,
            user=user,
        )

        items, total = await self.repo.get_requests(
            db,
            page=page,
            page_size=page_size,
            room_id=room_id,
            status=status,
            source=source,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # =========================
    # approve / reject
    # =========================

    async def approve_request(
        self,
        db: AsyncSession,
        *,
        request_id: int,
        user: User,
    ) -> RoomJoinRequest:
        request = await self.get_join_request_by_id(db, request_id)
        self._ensure_pending(request)

        if user.id == request.target_user_id:
            return await self._approve_by_target(db, request=request, user=user)

        await self._ensure_can_review_by_room(
            db,
            room_id=request.room_id,
            user=user,
        )
        return await self._approve_by_room(db, request=request, user=user)

    async def reject_request(
        self,
        db: AsyncSession,
        *,
        request_id: int,
        user: User,
    ) -> RoomJoinRequest:
        request = await self.get_join_request_by_id(db, request_id)
        self._ensure_pending(request)

        if user.id == request.target_user_id:
            return await self._reject_by_target(db, request=request, user=user)

        await self._ensure_can_review_by_room(
            db,
            room_id=request.room_id,
            user=user,
        )
        return await self._reject_by_room(db, request=request, user=user)

    # =========================
    # internal actions
    # =========================

    async def _approve_by_target(
        self,
        db: AsyncSession,
        *,
        request: RoomJoinRequest,
        user: User,
    ) -> RoomJoinRequest:
        if request.target_user_id != user.id:
            raise ForbiddenError("You do not have permission to perform this action")

        request.target_action = RoomJoinRequestAction.APPROVED
        request = await self._finalize(db, request)
        await db.commit()
        return await self.get_join_request_by_id(db, request.id)

    async def _approve_by_room(
        self,
        db: AsyncSession,
        *,
        request: RoomJoinRequest,
        user: User,
    ) -> RoomJoinRequest:
        request.room_action = RoomJoinRequestAction.APPROVED
        request.room_action_by_user_id = user.id

        request = await self._finalize(db, request)
        await db.commit()
        return await self.get_join_request_by_id(db, request.id)

    async def _reject_by_target(
        self,
        db: AsyncSession,
        *,
        request: RoomJoinRequest,
        user: User,
    ) -> RoomJoinRequest:
        if request.target_user_id != user.id:
            raise ForbiddenError("You do not have permission to perform this action")

        request.target_action = RoomJoinRequestAction.REJECTED

        request = await self._finalize(db, request)
        await db.commit()
        return await self.get_join_request_by_id(db, request.id)

    async def _reject_by_room(
        self,
        db: AsyncSession,
        *,
        request: RoomJoinRequest,
        user: User,
    ) -> RoomJoinRequest:
        request.room_action = RoomJoinRequestAction.REJECTED
        request.room_action_by_user_id = user.id

        request = await self._finalize(db, request)
        await db.commit()
        return await self.get_join_request_by_id(db, request.id)

    # =========================
    # internal helpers
    # =========================

    def _ensure_pending(self, request: RoomJoinRequest) -> None:
        if request.status != RoomJoinRequestStatus.PENDING:
            raise BadRequestError("Request already handled.")

    async def _ensure_no_pending_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        target_user_id: int,
    ) -> None:
        existing = await self.repo.get_pending_request(
            db,
            room_id=room_id,
            target_user_id=target_user_id,
        )
        if existing:
            raise ConflictError("Pending request already exists.")

    async def _ensure_user_not_member(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
    ) -> None:
        member = await self.membership_service.find_room_member(
            db,
            room_id=room_id,
            user_id=user_id,
        )
        if member:
            raise ConflictError("User is already a room member.")

    async def _ensure_can_invite(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.INVITE_USER)

    async def _ensure_can_review_by_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=user.id,
        )
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, RoomPermission.REVIEW_JOIN_REQUEST)

    async def _finalize(
        self,
        db: AsyncSession,
        request: RoomJoinRequest,
    ) -> RoomJoinRequest:
        if (
            request.room_action == RoomJoinRequestAction.REJECTED
            or request.target_action == RoomJoinRequestAction.REJECTED
        ):
            request.status = RoomJoinRequestStatus.REJECTED

            # TODO: notify the side which did not reject
            return await self.repo.save_request(db, request)

        if (
            request.room_action == RoomJoinRequestAction.APPROVED
            and request.target_action == RoomJoinRequestAction.APPROVED
        ):
            request.status = RoomJoinRequestStatus.APPROVED

            await self.membership_service.add_member(
                db,
                room_id=request.room_id,
                user_id=request.target_user_id,
                role=RoomRole.MEMBER,
            )

            # TODO: notify success
            return await self.repo.save_request(db, request)

        return await self.repo.save_request(db, request)