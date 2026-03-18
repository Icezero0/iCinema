from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.rooms.join_request.schemas import RoomJoinRequestResponse
from app.modules.rooms.join_request.service import RoomJoinRequestService
from app.modules.users.models import User

router = APIRouter(prefix="/join-requests", tags=["join-requests"])

join_request_service = RoomJoinRequestService()


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
) -> RoomJoinRequestResponse:
    request = await join_request_service.approve_request(
        db,
        request_id=request_id,
        user=current_user,
    )
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
