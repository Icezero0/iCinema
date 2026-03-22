from datetime import datetime, timedelta, timezone

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.modules.media.constants import (
    MediaAssetStatus,
    MediaAssetType,
    StickerLibrarySource,
)
from app.modules.media.models import MediaAsset
from app.modules.media.repository import MediaRepository
from app.modules.media.storage import MediaStorageService
from app.modules.users.models import User

settings = get_settings()


class MediaService:
    def __init__(self) -> None:
        self.repo = MediaRepository()
        self.storage = MediaStorageService()

    async def find_media_asset_by_id(self, db: AsyncSession, asset_id: int) -> MediaAsset | None:
        return await self.repo.find_media_asset_by_id(db, asset_id)

    async def get_media_asset_by_id(self, db: AsyncSession, asset_id: int) -> MediaAsset:
        asset = await self.find_media_asset_by_id(db, asset_id)
        if not asset:
            raise NotFoundError("Media asset not found")
        return asset

    def get_media_asset_url(self, asset: MediaAsset) -> str:
        if asset.asset_type == MediaAssetType.AVATAR:
            return f"{settings.avatar_public_prefix}/{asset.storage_key}"
        if asset.asset_type == MediaAssetType.IMAGE:
            return f"{settings.image_public_prefix}/{asset.storage_key}"
        if asset.asset_type == MediaAssetType.STICKER:
            return f"{settings.sticker_public_prefix}/{asset.storage_key}"
        if asset.asset_type == MediaAssetType.VIDEO:
            return f"{settings.video_public_prefix}/{asset.storage_key}"
        raise NotFoundError("Unsupported media asset type")

    async def create_avatar_asset(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        user: User,
    ) -> MediaAsset:
        prepared = await self.storage.prepare_upload(
            file=file,
            asset_type=MediaAssetType.AVATAR,
        )

        asset = await self.repo.find_media_asset_by_type_and_sha256(
            db,
            asset_type=MediaAssetType.AVATAR,
            sha256=prepared.sha256,
        )
        if asset is None:
            saved = self.storage.save_prepared_upload(
                prepared=prepared,
                asset_type=MediaAssetType.AVATAR,
            )
            asset = await self.repo.create_media_asset(
                db,
                asset_type=MediaAssetType.AVATAR,
                storage_key=saved.storage_key,
                mime_type=saved.mime_type,
                file_size=saved.file_size,
                width=saved.width,
                height=saved.height,
                duration_seconds=saved.duration_seconds,
                sha256=saved.sha256,
                uploaded_by_user_id=user.id,
                status=MediaAssetStatus.ACTIVE,
                expires_at=None,
            )

        await self.repo.soft_delete_active_user_avatar_assets(db, user.id)
        await self.repo.create_user_avatar_asset(
            db,
            user_id=user.id,
            media_asset_id=asset.id,
        )

        user.avatar_key = asset.storage_key
        return asset

    async def create_image_asset(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        user: User,
    ) -> MediaAsset:
        prepared = await self.storage.prepare_upload(
            file=file,
            asset_type=MediaAssetType.IMAGE,
        )

        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        asset = await self.repo.find_media_asset_by_type_and_sha256(
            db,
            asset_type=MediaAssetType.IMAGE,
            sha256=prepared.sha256,
        )
        if asset is not None:
            await self.repo.touch_image_asset_expiry(
                db,
                asset_id=asset.id,
                expires_at=expires_at,
            )
            await db.refresh(asset)
            return asset

        saved = self.storage.save_prepared_upload(
            prepared=prepared,
            asset_type=MediaAssetType.IMAGE,
        )
        asset = await self.repo.create_media_asset(
            db,
            asset_type=MediaAssetType.IMAGE,
            storage_key=saved.storage_key,
            mime_type=saved.mime_type,
            file_size=saved.file_size,
            width=saved.width,
            height=saved.height,
            duration_seconds=saved.duration_seconds,
            sha256=saved.sha256,
            uploaded_by_user_id=user.id,
            status=MediaAssetStatus.ACTIVE,
            expires_at=expires_at,
        )
        return asset

    async def create_sticker_asset(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        user: User,
    ) -> MediaAsset:
        prepared = await self.storage.prepare_upload(
            file=file,
            asset_type=MediaAssetType.STICKER,
        )

        existing = await self.repo.find_media_asset_by_type_and_sha256(
            db,
            asset_type=MediaAssetType.STICKER,
            sha256=prepared.sha256,
        )
        if existing:
            item = await self.repo.find_user_sticker_library_item(
                db,
                user_id=user.id,
                media_asset_id=existing.id,
            )
            if not item:
                await self.repo.create_user_sticker_library_item(
                    db,
                    user_id=user.id,
                    media_asset_id=existing.id,
                    source=StickerLibrarySource.UPLOAD,
                )
            return existing

        saved = self.storage.save_prepared_upload(
            prepared=prepared,
            asset_type=MediaAssetType.STICKER,
        )
        asset = await self.repo.create_media_asset(
            db,
            asset_type=MediaAssetType.STICKER,
            storage_key=saved.storage_key,
            mime_type=saved.mime_type,
            file_size=saved.file_size,
            width=saved.width,
            height=saved.height,
            duration_seconds=saved.duration_seconds,
            sha256=saved.sha256,
            uploaded_by_user_id=user.id,
            status=MediaAssetStatus.ACTIVE,
            expires_at=None,
        )

        await self.repo.create_user_sticker_library_item(
            db,
            user_id=user.id,
            media_asset_id=asset.id,
            source=StickerLibrarySource.UPLOAD,
        )
        return asset

    async def get_serving_asset(self, db: AsyncSession, asset_id: int) -> MediaAsset:
        asset = await self.get_media_asset_by_id(db, asset_id)

        if asset.status == MediaAssetStatus.DELETED:
            raise NotFoundError("Media asset not found")
        if asset.status == MediaAssetStatus.EXPIRED:
            raise NotFoundError("Media asset expired")

        return asset
    
    async def get_user_avatar_url(
        self,
        db,
        user_id: int,
    ) -> str | None:
        asset = await self.repo.find_active_avatar_asset_by_user_id(db, user_id)
        if not asset:
            return None
        return self.get_media_asset_url(asset)

    async def get_user_avatar_storage_key(
        self,
        db,
        user_id: int,
    ) -> str | None:
        asset = await self.repo.find_active_avatar_asset_by_user_id(db, user_id)
        if not asset:
            return None
        return asset.storage_key
    
    async def get_user_avatar_storage_key_map(
        self,
        db,
        user_ids: list[int],
    ) -> dict[int, str | None]:
        if not user_ids:
            return {}

        rows = await self.repo.find_active_avatar_storage_keys_by_user_ids(db, user_ids)

        avatar_key_map: dict[int, str | None] = {user_id: None for user_id in user_ids}

        for user_id, storage_key in rows:
            if avatar_key_map[user_id] is None:
                avatar_key_map[user_id] = storage_key

        return avatar_key_map
    
    async def get_media_assets_by_ids(
        self,
        db: AsyncSession,
        asset_ids: list[int],
    ) -> list[MediaAsset]:
        return await self.repo.get_media_assets_by_ids(db, asset_ids)