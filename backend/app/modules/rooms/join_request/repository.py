from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rooms.constants import (
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomJoinRequestAction,
)
from app.modules.rooms.models import RoomJoinRequest


class RoomJoinRequestRepository:
    async def create_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        initiator_user_id: int,
        target_user_id: int,
        source: RoomJoinRequestSource,
        status: RoomJoinRequestStatus,
        room_action: RoomJoinRequestAction,
        target_action: RoomJoinRequestAction,
        room_action_by_user_id: int | None = None,
    ) -> RoomJoinRequest:
        request = RoomJoinRequest(
            room_id=room_id,
            initiator_user_id=initiator_user_id,
            target_user_id=target_user_id,
            source=source,
            status=status,
            room_action=room_action,
            target_action=target_action,
            room_action_by_user_id=room_action_by_user_id,
        )
        db.add(request)
        await db.flush()
        await db.refresh(request)
        return request

    async def get_request_by_id(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> RoomJoinRequest | None:
        result = await db.execute(
            select(RoomJoinRequest)
            .where(RoomJoinRequest.id == request_id)
            .options(
                selectinload(RoomJoinRequest.room),
                selectinload(RoomJoinRequest.initiator),
                selectinload(RoomJoinRequest.target),
                selectinload(RoomJoinRequest.room_action_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_request(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        target_user_id: int,
    ) -> RoomJoinRequest | None:
        result = await db.execute(
            select(RoomJoinRequest)
            .where(
                RoomJoinRequest.room_id == room_id,
                RoomJoinRequest.target_user_id == target_user_id,
                RoomJoinRequest.status == RoomJoinRequestStatus.PENDING,
            )
            .options(
                selectinload(RoomJoinRequest.room),
                selectinload(RoomJoinRequest.initiator),
                selectinload(RoomJoinRequest.target),
                selectinload(RoomJoinRequest.room_action_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_requests(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        room_ids: list[int] | None = None,
        room_id: int | None = None,
        initiator_user_id: int | None = None,
        target_user_id: int | None = None,
        status: RoomJoinRequestStatus | None = None,
        source: RoomJoinRequestSource | None = None,
        related_user_id: int | None = None,
        include_room_ids_for_related: list[int] | None = None,
        visible_target_user_id: int | None = None,
    ) -> tuple[list[RoomJoinRequest], int]:
        stmt = select(RoomJoinRequest).options(
            selectinload(RoomJoinRequest.room),
            selectinload(RoomJoinRequest.initiator),
            selectinload(RoomJoinRequest.target),
            selectinload(RoomJoinRequest.room_action_by),
        )

        count_stmt = select(func.count(RoomJoinRequest.id))

        if room_ids is not None:
            if not room_ids:
                return [], 0
            stmt = stmt.where(RoomJoinRequest.room_id.in_(room_ids))
            count_stmt = count_stmt.where(RoomJoinRequest.room_id.in_(room_ids))

        if room_id is not None:
            stmt = stmt.where(RoomJoinRequest.room_id == room_id)
            count_stmt = count_stmt.where(RoomJoinRequest.room_id == room_id)

        if initiator_user_id is not None:
            stmt = stmt.where(
                RoomJoinRequest.initiator_user_id == initiator_user_id
            )
            count_stmt = count_stmt.where(
                RoomJoinRequest.initiator_user_id == initiator_user_id
            )

        if target_user_id is not None:
            stmt = stmt.where(RoomJoinRequest.target_user_id == target_user_id)
            count_stmt = count_stmt.where(
                RoomJoinRequest.target_user_id == target_user_id
            )

        if status is not None:
            stmt = stmt.where(RoomJoinRequest.status == status)
            count_stmt = count_stmt.where(RoomJoinRequest.status == status)

        if source is not None:
            stmt = stmt.where(RoomJoinRequest.source == source)
            count_stmt = count_stmt.where(RoomJoinRequest.source == source)

        if related_user_id is not None:
            related_filter = or_(
                RoomJoinRequest.initiator_user_id == related_user_id,
                RoomJoinRequest.target_user_id == related_user_id,
                RoomJoinRequest.room_action_by_user_id == related_user_id,
            )
            if include_room_ids_for_related:
                related_filter = or_(
                    related_filter,
                    RoomJoinRequest.room_id.in_(include_room_ids_for_related),
            )
            stmt = stmt.where(related_filter)
            count_stmt = count_stmt.where(related_filter)
        elif visible_target_user_id is not None or include_room_ids_for_related:
            visibility_conditions = []
            if visible_target_user_id is not None:
                visibility_conditions.append(
                    and_(
                        RoomJoinRequest.target_user_id == visible_target_user_id,
                        RoomJoinRequest.source.in_(
                            [
                                RoomJoinRequestSource.INVITE,
                                RoomJoinRequestSource.MEMBER_INVITE,
                            ]
                        ),
                    )
                )
            if include_room_ids_for_related:
                visibility_conditions.append(
                    RoomJoinRequest.room_id.in_(include_room_ids_for_related)
                )

            visibility_filter = or_(*visibility_conditions)
            stmt = stmt.where(visibility_filter)
            count_stmt = count_stmt.where(visibility_filter)

        stmt = (
            stmt.order_by(RoomJoinRequest.created_at.desc(), RoomJoinRequest.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())

        total = await db.scalar(count_stmt)
        return items, int(total or 0)

    async def save_request(
        self,
        db: AsyncSession,
        request: RoomJoinRequest,
    ) -> RoomJoinRequest:
        db.add(request)
        await db.flush()
        await db.refresh(request)
        return request
