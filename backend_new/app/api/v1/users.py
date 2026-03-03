from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import AvatarUploadResponse, UserMeResponse, UserPatch
from app.modules.users.service import UserService

from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/users", tags=["users"])

user_service = UserService()


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse.model_validate(current_user)


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
        return AvatarUploadResponse(avatar_url="")
    return AvatarUploadResponse(
        avatar_url=f"{settings.avatar_public_prefix}/{updated.avatar_key}"
    )