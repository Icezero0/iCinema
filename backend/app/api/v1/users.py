from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.rooms.constants import RoomRole
from app.modules.rooms.room.schemas import (
    UserRoomSummaryListResponse,
    UserRoomSummaryResponse,
)
from app.modules.users.models import User
from app.modules.users.schemas import (
    AvatarUploadResponse,
    UserListResponse,
    UserMeResponse,
    UserPatch,
    UserResponse,
)
from app.modules.users.service import UserService

settings = get_settings()

router = APIRouter(prefix="/users", tags=["users"])

user_service = UserService()


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserMeResponse:
    user = await user_service.get_user_by_id(db, current_user.id)
    return UserMeResponse.model_validate(user)


@router.patch("/me", response_model=UserMeResponse)
async def patch_me(
    payload: UserPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserMeResponse:
    updated = await user_service.patch_me(db, current_user, payload)
    return UserMeResponse.model_validate(updated)


@router.patch("/me/avatar", response_model=AvatarUploadResponse)
async def patch_my_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AvatarUploadResponse:
    updated = await user_service.update_avatar(db, current_user, file)
    if not updated.avatar_key:
        return AvatarUploadResponse(avatar_url=None)

    return AvatarUploadResponse(
        avatar_url=f"{settings.avatar_public_prefix}/{updated.avatar_key}"
    )


@router.get("/me/rooms", response_model=UserRoomSummaryListResponse)
async def get_my_rooms(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: RoomRole | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRoomSummaryListResponse:
    data = await user_service.get_my_rooms(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        role=role,
    )
    return UserRoomSummaryListResponse(
        items=[
            UserRoomSummaryResponse(
                id=room.id,
                name=room.name,
                owner_id=room.owner_id,
                owner=room.owner,
                my_role=my_role,
                visibility=room.visibility,
            )
            for room, my_role in data["items"]
        ],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/me/owned-rooms", response_model=UserRoomSummaryListResponse)
async def get_my_owned_rooms(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRoomSummaryListResponse:
    data = await user_service.get_my_owned_rooms(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
    )
    return UserRoomSummaryListResponse(
        items=[
            UserRoomSummaryResponse(
                id=room.id,
                name=room.name,
                owner_id=room.owner_id,
                owner=room.owner,
                my_role=my_role,
                visibility=room.visibility,
            )
            for room, my_role in data["items"]
        ],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("", response_model=UserListResponse)
async def get_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    username: str | None = Query(default=None),
    email: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserListResponse:
    data = await user_service.get_users(
        db,
        page=page,
        page_size=page_size,
        username=username,
        email=email,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    user = await user_service.get_user_by_id(db, user_id)
    return UserResponse.model_validate(user)
