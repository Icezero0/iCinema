from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.media.schemas import MediaAssetUploadResponse
from app.modules.media.service import MediaService
from app.modules.users.models import User

router = APIRouter(prefix="/media", tags=["media"])

media_service = MediaService()


@router.post("/images", response_model=MediaAssetUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaAssetUploadResponse:
    asset = await media_service.create_image_asset(
        db,
        file=file,
        user=current_user,
    )
    await db.commit()
    return MediaAssetUploadResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        url=media_service.get_media_asset_url(asset),
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        status=asset.status,
    )


@router.post("/stickers", response_model=MediaAssetUploadResponse)
async def upload_sticker(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaAssetUploadResponse:
    asset = await media_service.create_sticker_asset(
        db,
        file=file,
        user=current_user,
    )
    await db.commit()
    return MediaAssetUploadResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        url=media_service.get_media_asset_url(asset),
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        status=asset.status,
    )