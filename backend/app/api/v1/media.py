from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.media.schemas import (
    EmojiListResponse,
    EmojiResponse,
    MediaAssetUploadResponse,
    StickerLibraryResponse,
    StickerLibraryUpdateRequest,
    StickerResponse,
)
from app.modules.media.service import MediaService
from app.modules.users.models import User
from app.core.exceptions import BadRequestError

router = APIRouter(prefix="/media", tags=["media"])

media_service = MediaService()


def _build_sticker_response(item, asset) -> StickerResponse:
    return StickerResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        width=asset.width,
        height=asset.height,
        status=asset.status,
        sort_order=item.sort_order,
        url=media_service.get_media_asset_url(asset),
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


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
    return MediaAssetUploadResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        url=media_service.get_media_asset_url(asset),
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        status=asset.status,
    )


@router.get("/stickers/library", response_model=StickerLibraryResponse)
async def get_my_stickers(
    all: bool = Query(default=False),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StickerLibraryResponse:
    if all and not (page is None and page_size is None):
        raise BadRequestError("page and page_size are not allowed when all=true")
    data = await media_service.get_user_sticker_library(
        db,
        user=current_user,
        all=all,
        page=page,
        page_size=page_size,
    )
    return StickerLibraryResponse(
        items=[
            _build_sticker_response(item, asset)
            for item, asset in data["items"]
        ],
        total=data["total"],
        all=data["all"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.post("/stickers/{sticker_id}/collect", response_model=StickerResponse)
async def collect_sticker(
    sticker_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StickerResponse:
    asset = await media_service.collect_sticker(
        db,
        sticker_id=sticker_id,
        user=current_user,
    )

    item = await media_service.get_user_sticker_library_item(
        db,
        user_id=current_user.id,
        media_asset_id=asset.id,
    )
    if item is None:
        raise RuntimeError("Sticker library item not found after collect")

    return _build_sticker_response(item, asset)


@router.patch("/stickers/library")
async def update_user_sticker_library(
    payload: StickerLibraryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    await media_service.update_user_sticker_library(
        db,
        user=current_user,
        sticker_ids=payload.sticker_ids,
    )
    return {"message": "ok"}


@router.get("/emojis", response_model=EmojiListResponse)
async def get_emojis() -> EmojiListResponse:
    items = await media_service.get_visible_emojis()
    return EmojiListResponse(
        items=[EmojiResponse(**item) for item in items],
    )


@router.get("/emojis/recent", response_model=EmojiListResponse)
async def get_recent_emojis(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmojiListResponse:
    items = await media_service.get_recent_emojis(
        db,
        user_id=current_user.id,
        limit=limit,
    )
    return EmojiListResponse(
        items=[EmojiResponse(**item) for item in items],
    )