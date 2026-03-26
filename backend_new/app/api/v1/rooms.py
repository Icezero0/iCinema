from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.rooms.constants import (
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
)
from app.modules.rooms.join_request.schemas import (
    RoomJoinRequestCreate,
    RoomJoinRequestListResponse,
    RoomJoinRequestResponse,
)
from app.modules.rooms.join_request.service import RoomJoinRequestService
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
from app.modules.rooms.settings.schemas import (
    RoomSettingsPatch,
    RoomSettingsResponse,
)
from app.modules.rooms.settings.service import RoomSettingsService
from app.modules.rooms.room.service import RoomService
from app.modules.users.models import User

router = APIRouter(prefix="/rooms", tags=["rooms"])

room_service = RoomService()
membership_service = RoomMembershipService()
join_request_service = RoomJoinRequestService()
settings_service = RoomSettingsService()


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


@router.get("/{room_id}/settings", response_model=RoomSettingsResponse)
async def get_room_settings(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomSettingsResponse:
    settings = await settings_service.get_accessible_room_settings_by_room_id(
        db,
        room_id=room_id,
        user=current_user,
    )
    return RoomSettingsResponse.model_validate(settings)


@router.patch("/{room_id}/settings", response_model=RoomSettingsResponse)
async def patch_room_settings(
    room_id: int,
    payload: RoomSettingsPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomSettingsResponse:
    settings = await settings_service.patch_room_settings(
        db,
        room_id=room_id,
        user=current_user,
        payload=payload,
    )
    return RoomSettingsResponse.model_validate(settings)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    await room_service.delete_room(db, room_id=room_id, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/{room_id}/join-requests", response_model=RoomJoinRequestListResponse)
async def get_room_join_requests(
    room_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_: RoomJoinRequestStatus | None = Query(default=None, alias="status"),
    source: RoomJoinRequestSource | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomJoinRequestListResponse:
    data = await join_request_service.get_room_join_requests(
        db,
        room_id=room_id,
        user=current_user,
        page=page,
        page_size=page_size,
        status=status_,
        source=source,
    )
    return RoomJoinRequestListResponse(
        items=[RoomJoinRequestResponse.model_validate(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.post(
    "/{room_id}/join-requests/apply",
    status_code=status.HTTP_200_OK,
)
async def apply_room_join_request(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await join_request_service.create_apply_request(
        db,
        room_id=room_id,
        user=current_user,
    )


@router.post(
    "/{room_id}/join-requests/invite",
    status_code=status.HTTP_200_OK,
)
async def invite_room_join_request(
    room_id: int,
    payload: RoomJoinRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await join_request_service.create_invite_request(
        db,
        room_id=room_id,
        target_user_id=payload.target_user_id,
        user=current_user,
    )


@router.delete(
    "/{room_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_room_member(
    room_id: int,
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    await membership_service.remove_room_member(
        db,
        room_id=room_id,
        target_user_id=target_user_id,
        current_user=current_user,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
