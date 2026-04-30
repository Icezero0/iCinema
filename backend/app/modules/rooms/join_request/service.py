from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.modules.rooms.constants import (
    RoomJoinAuditMode,
    RoomJoinRequestAction,
    RoomJoinRequestListScope,
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomPermission,
    RoomRole,
)
from app.modules.rooms.join_request.repository import RoomJoinRequestRepository
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.models import RoomJoinRequest
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.room.service import RoomService
from app.modules.users.models import User
from app.modules.users.service import UserService

from app.modules.notifications.constants import (
    NotificationRelatedType,
    NotificationType,
)
from app.modules.notifications.schemas import NotificationCreate
from app.modules.notifications.service import NotificationService


class RoomJoinRequestService:
    def __init__(self) -> None:
        self.repo = RoomJoinRequestRepository()
        self.membership_service = RoomMembershipService()
        self.room_service = RoomService()
        self.user_service = UserService()
        self.notification_service = NotificationService()

    # =========================
    # create
    # =========================

    async def create_apply_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> RoomJoinRequest | None:
        room = await self.room_service.get_room_by_id(db, room_id)

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

        if room.join_audit_mode == RoomJoinAuditMode.AUTO_REJECT:
            raise ForbiddenError(
                "This room is not accepting join requests.",
                reason=ErrorReason.ROOM_NOT_ACCEPTING_JOIN_REQUESTS,
                details={"room_id": room_id, "join_audit_mode": room.join_audit_mode},
            )

        if room.join_audit_mode == RoomJoinAuditMode.AUTO_APPROVE:
            await self.membership_service.add_room_member_in_tx(
                db,
                room_id=room_id,
                user_id=user.id,
                role=RoomRole.MEMBER,
            )
            await db.commit()
            return None

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

        reviewer_user_ids = await self.membership_service.get_room_user_ids_by_permission(
            db,
            room_id=room_id,
            permission=RoomPermission.REVIEW_JOIN_REQUEST,
        )

        for reviewer_user_id in reviewer_user_ids:
            if reviewer_user_id == user.id:
                continue
            await self._send_room_join_request_notification(
                db,
                recipient_user_id=reviewer_user_id,
                request_id=request.id,
            )

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

        role = await self._require_room_permission(
            db,
            room_id=room_id,
            user=user,
            permission=RoomPermission.INVITE_USER,
        )

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

        can_review = True
        try:
            require_room_permission(role, RoomPermission.REVIEW_JOIN_REQUEST)
        except ForbiddenError:
            can_review = False

        room_action = (
            RoomJoinRequestAction.APPROVED
            if can_review
            else RoomJoinRequestAction.PENDING
        )
        source = (
            RoomJoinRequestSource.INVITE
            if can_review
            else RoomJoinRequestSource.MEMBER_INVITE
        )
        room_action_by_user_id = user.id if can_review else None

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

        await self._send_room_join_request_notification(
            db,
            recipient_user_id=target_user_id,
            request_id=request.id,
        )

        if not can_review:
            reviewer_user_ids = await self.membership_service.get_room_user_ids_by_permission(
                db,
                room_id=room_id,
                permission=RoomPermission.REVIEW_JOIN_REQUEST,
            )

            for reviewer_user_id in reviewer_user_ids:
                if reviewer_user_id == user.id:
                    continue
                await self._send_room_join_request_notification(
                    db,
                    recipient_user_id=reviewer_user_id,
                    request_id=request.id,
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
            raise NotFoundError(
                "Join request not found.",
                reason=ErrorReason.JOIN_REQUEST_NOT_FOUND,
                details={"request_id": request_id},
            )
        return request

    async def get_accessible_join_request_by_id(
        self,
        db: AsyncSession,
        *,
        request_id: int,
        user: User,
    ) -> RoomJoinRequest:
        request = await self.get_join_request_by_id(db, request_id)

        if user.id == request.target_user_id:
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

    async def get_join_requests(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
        status: RoomJoinRequestStatus | None = None,
        room_id: int | None = None,
        initiator_user_id: int | None = None,
        target_user_id: int | None = None,
        scope: RoomJoinRequestListScope = RoomJoinRequestListScope.ALL_RELATED_TO_ME,
    ) -> dict:
        reviewer_room_ids: list[int] = []
        if scope in {
            RoomJoinRequestListScope.HANDLED_BY_ME,
            RoomJoinRequestListScope.ALL_RELATED_TO_ME,
        }:
            reviewer_room_ids = await self.membership_service.get_room_ids_by_permission(
                db,
                user_id=user.id,
                permission=RoomPermission.REVIEW_JOIN_REQUEST,
            )

        repo_room_ids: list[int] | None = None
        repo_initiator_user_id = initiator_user_id
        repo_target_user_id = target_user_id
        repo_related_user_id: int | None = None
        repo_visible_target_user_id: int | None = None

        if scope == RoomJoinRequestListScope.HANDLED_BY_ME:
            repo_visible_target_user_id = user.id
        elif scope == RoomJoinRequestListScope.CREATED_BY_ME:
            repo_initiator_user_id = user.id
        else:
            repo_related_user_id = user.id

        items, total = await self.repo.get_requests(
            db,
            page=page,
            page_size=page_size,
            room_ids=repo_room_ids,
            room_id=room_id,
            initiator_user_id=repo_initiator_user_id,
            target_user_id=repo_target_user_id,
            status=status,
            related_user_id=repo_related_user_id,
            include_room_ids_for_related=reviewer_room_ids,
            visible_target_user_id=repo_visible_target_user_id,
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
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.JOIN_REQUEST_TARGET_ACTION_FORBIDDEN,
                details={"request_id": request.id, "target_user_id": request.target_user_id},
            )

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
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.JOIN_REQUEST_TARGET_ACTION_FORBIDDEN,
                details={"request_id": request.id, "target_user_id": request.target_user_id},
            )

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
            raise BadRequestError(
                "Request already handled.",
                reason=ErrorReason.JOIN_REQUEST_ALREADY_HANDLED,
                details={"request_id": request.id, "status": request.status},
            )

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
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.ROOM_PERMISSION_DENIED,
                details={"room_id": room_id, "permission": permission},
            )

        require_room_permission(role, permission)
        return role

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
            raise ConflictError(
                "Pending request already exists.",
                reason=ErrorReason.PENDING_JOIN_REQUEST_ALREADY_EXISTS,
                details={
                    "room_id": room_id,
                    "target_user_id": target_user_id,
                    "request_id": existing.id,
                },
            )

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
            raise ConflictError(
                "User is already a room member.",
                reason=ErrorReason.USER_ALREADY_ROOM_MEMBER,
                details={"room_id": room_id, "user_id": user_id},
            )

    async def _ensure_can_review_by_room(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
    ) -> None:
        await self._require_room_permission(
            db,
            room_id=room_id,
            user=user,
            permission=RoomPermission.REVIEW_JOIN_REQUEST,
        )

    async def _send_room_join_request_notification(
        self,
        db: AsyncSession,
        *,
        recipient_user_id: int,
        request_id: int,
    ) -> None:
        await self.notification_service.create_notification_in_tx(
            db,
            payload=NotificationCreate(
                recipient_user_id=recipient_user_id,
                actor_user_id=None,
                notification_type=NotificationType.WORKFLOW,
                related_type=NotificationRelatedType.ROOM_JOIN_REQUEST,
                related_id=request_id,
            ),
        )

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
            return await self.repo.save_request(db, request)

        if (
            request.room_action == RoomJoinRequestAction.APPROVED
            and request.target_action == RoomJoinRequestAction.APPROVED
        ):
            request.status = RoomJoinRequestStatus.APPROVED

            await self.membership_service.add_room_member_in_tx(
                db,
                room_id=request.room_id,
                user_id=request.target_user_id,
                role=RoomRole.MEMBER,
            )

            return await self.repo.save_request(db, request)

        return await self.repo.save_request(db, request)
