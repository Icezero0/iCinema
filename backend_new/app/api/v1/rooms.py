from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.rooms.membership.schemas import (
    RoomMemberListResponse,
    RoomMemberResponse,
)
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.schemas import (
    RoomCreate,
    RoomListResponse,
    RoomPatch,
    RoomResponse,
)
from app.modules.rooms.room.service import RoomService
from app.modules.users.models import User

router = APIRouter(prefix="/rooms", tags=["rooms"])

room_service = RoomService()
membership_service = RoomMembershipService()


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomResponse:
    room = await room_service.create_room(db, user=current_user, payload=payload)
    return RoomResponse.model_validate(room)


@router.get("", response_model=RoomListResponse)
async def get_rooms(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomListResponse:
    data = await room_service.get_rooms(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        name=name,
    )
    return RoomListResponse(
        items=[RoomResponse.model_validate(room) for room in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomResponse:
    room = await room_service.get_accessible_room_by_id(
        db,
        room_id=room_id,
        user=current_user,
    )
    return RoomResponse.model_validate(room)


@router.get("/{room_id}/members", response_model=RoomMemberListResponse)
async def get_room_members(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomMemberListResponse:
    await room_service.get_room_by_id(db, room_id)

    data = await membership_service.get_room_members(
        db,
        room_id=room_id,
        user=current_user,
    )
    return RoomMemberListResponse(
        items=[RoomMemberResponse.model_validate(member) for member in data["items"]],
        total=data["total"],
    )


@router.patch("/{room_id}", response_model=RoomResponse)
async def patch_room(
    room_id: int,
    payload: RoomPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomResponse:
    room = await room_service.patch_room(
        db,
        room_id=room_id,
        user=current_user,
        payload=payload,
    )
    return RoomResponse.model_validate(room)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    await room_service.delete_room(db, room_id=room_id, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)