from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_realtime_publisher
from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.rooms.constants import (
    RoomJoinRequestListScope,
    RoomJoinRequestStatus,
)
from app.modules.rooms.join_request.schemas import (
    RoomJoinRequestListResponse,
    RoomJoinRequestResponse,
)
from app.modules.rooms.join_request.service import RoomJoinRequestService
from app.modules.users.models import User
from app.realtime.publisher import RealtimePublisher

router = APIRouter(prefix="/join-requests", tags=["join-requests"])

join_request_service = RoomJoinRequestService()


@router.get("", response_model=RoomJoinRequestListResponse)
async def get_join_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: RoomJoinRequestStatus | None = Query(default=None),
    room_id: int | None = Query(default=None, ge=1),
    initiator_user_id: int | None = Query(default=None, ge=1),
    target_user_id: int | None = Query(default=None, ge=1),
    scope: RoomJoinRequestListScope = Query(default=RoomJoinRequestListScope.ALL_RELATED_TO_ME),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomJoinRequestListResponse:
    data = await join_request_service.get_join_requests(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        room_id=room_id,
        initiator_user_id=initiator_user_id,
        target_user_id=target_user_id,
        scope=scope,
    )
    return RoomJoinRequestListResponse(
        items=[RoomJoinRequestResponse.model_validate(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/{request_id}", response_model=RoomJoinRequestResponse)
async def get_join_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomJoinRequestResponse:
    request = await join_request_service.get_accessible_join_request_by_id(
        db,
        request_id=request_id,
        user=current_user,
    )
    return RoomJoinRequestResponse.model_validate(request)


@router.post("/{request_id}/approve", response_model=RoomJoinRequestResponse)
async def approve_join_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    publisher: RealtimePublisher = Depends(get_realtime_publisher),
) -> RoomJoinRequestResponse:
    request = await join_request_service.approve_request(
        db,
        request_id=request_id,
        user=current_user,
    )
    if request.status == RoomJoinRequestStatus.APPROVED:
        await publisher.publish_room_members(room_id=request.room_id)
    return RoomJoinRequestResponse.model_validate(request)


@router.post("/{request_id}/reject", response_model=RoomJoinRequestResponse)
async def reject_join_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomJoinRequestResponse:
    request = await join_request_service.reject_request(
        db,
        request_id=request_id,
        user=current_user,
    )
    return RoomJoinRequestResponse.model_validate(request)
