from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.error_reasons import ErrorReason
from app.core.exceptions import NotFoundError
from app.modules.media.constants import MediaAssetType
from app.modules.media.repository import MediaRepository
from app.modules.media.service import MediaService

router = APIRouter(tags=["public-resources"])

repo = MediaRepository()
media_service = MediaService()


async def _serve_media_file(
    *,
    db: AsyncSession,
    asset_type: str,
    storage_key: str,
) -> FileResponse:
    asset = await repo.find_media_asset_by_type_and_storage_key(
        db,
        asset_type=asset_type,
        storage_key=storage_key,
    )
    if not asset:
        raise NotFoundError(
            "Media asset not found",
            reason=ErrorReason.MEDIA_ASSET_NOT_FOUND,
            details={"asset_type": asset_type},
        )

    # 惰性过期：如果是 image 且逻辑上已过期，这里会顺手把它标成 expired
    asset = await media_service.expire_asset_if_needed(db, asset)

    # 统一判定是否还能服务
    if media_service.is_asset_expired(asset):
        raise NotFoundError(
            "Media asset not found",
            reason=ErrorReason.MEDIA_ASSET_NOT_FOUND,
            details={"asset_type": asset_type, "asset_id": asset.id},
        )

    path = media_service.storage.get_file_path(
        asset_type=asset.asset_type,
        storage_key=asset.storage_key,
    )

    if not path.exists():
        raise NotFoundError(
            "Media file not found",
            reason=ErrorReason.MEDIA_FILE_NOT_FOUND,
            details={"asset_type": asset.asset_type, "asset_id": asset.id},
        )

    return FileResponse(
        str(path),
        media_type=asset.mime_type,
    )


@router.get("/avatar/{storage_key}")
async def get_avatar_file(
    storage_key: str,
    db: AsyncSession = Depends(get_db),
):
    return await _serve_media_file(
        db=db,
        asset_type=MediaAssetType.AVATAR,
        storage_key=storage_key,
    )


@router.get("/image/{storage_key}")
async def get_image_file(
    storage_key: str,
    db: AsyncSession = Depends(get_db),
):
    return await _serve_media_file(
        db=db,
        asset_type=MediaAssetType.IMAGE,
        storage_key=storage_key,
    )


@router.get("/sticker/{storage_key}")
async def get_sticker_file(
    storage_key: str,
    db: AsyncSession = Depends(get_db),
):
    return await _serve_media_file(
        db=db,
        asset_type=MediaAssetType.STICKER,
        storage_key=storage_key,
    )
