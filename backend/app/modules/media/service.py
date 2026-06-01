from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError, NotFoundError
from app.modules.media.constants import (
    EmojiProvider,
    MediaAssetStatus,
    MediaAssetType,
    StickerLibrarySource,
)
from app.modules.media.emoji_catalog import EmojiCatalogService
from app.modules.media.models import MediaAsset
from app.modules.media.repository import MediaRepository
from app.modules.media.storage import MediaStorageService
from app.modules.users.models import User

settings = get_settings()


class MediaService:
    def __init__(self) -> None:
        self.repo = MediaRepository()
        self.storage = MediaStorageService()
        self.emoji_catalog = EmojiCatalogService()

    def _normalize_datetime_to_utc_aware(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    async def find_media_asset_by_id(self, db: AsyncSession, asset_id: int) -> MediaAsset | None:
        return await self.repo.find_media_asset_by_id(db, asset_id)

    async def get_media_asset_by_id(self, db: AsyncSession, asset_id: int) -> MediaAsset:
        asset = await self.find_media_asset_by_id(db, asset_id)
        if not asset:
            raise NotFoundError(
                "Media asset not found",
                reason=ErrorReason.MEDIA_ASSET_NOT_FOUND,
                details={"asset_id": asset_id},
            )
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
        raise NotFoundError(
            "Unsupported media asset type",
            reason=ErrorReason.UNSUPPORTED_MEDIA_ASSET_TYPE,
            details={"asset_id": asset.id, "asset_type": asset.asset_type},
        )

    async def create_avatar_asset_in_tx(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        user: User,
    ) -> MediaAsset:
        # This helper participates in the caller's transaction and does not commit.
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
            await db.commit()
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

        await db.commit()
        return asset

    async def create_feedback_image_asset_in_tx(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        user: User,
    ) -> MediaAsset:
        # Feedback screenshots are part of the feedback record transaction and do not expire.
        prepared = await self.storage.prepare_upload(
            file=file,
            asset_type=MediaAssetType.FEEDBACK_IMAGE,
        )

        saved = self.storage.save_prepared_upload(
            prepared=prepared,
            asset_type=MediaAssetType.FEEDBACK_IMAGE,
        )
        return await self.repo.create_media_asset(
            db,
            asset_type=MediaAssetType.FEEDBACK_IMAGE,
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
                next_sort_order = await self.repo.get_next_user_sticker_sort_order(
                    db,
                    user_id=user.id,
                )
                await self.repo.create_user_sticker_library_item(
                    db,
                    user_id=user.id,
                    media_asset_id=existing.id,
                    source=StickerLibrarySource.UPLOAD,
                    sort_order=next_sort_order,
                )
            await db.commit()
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

        next_sort_order = await self.repo.get_next_user_sticker_sort_order(
            db,
            user_id=user.id,
        )
        await self.repo.create_user_sticker_library_item(
            db,
            user_id=user.id,
            media_asset_id=asset.id,
            source=StickerLibrarySource.UPLOAD,
            sort_order=next_sort_order,
        )
        
        await db.commit()
        return asset

    async def collect_sticker(
        self,
        db: AsyncSession,
        *,
        sticker_id: int,
        user: User,
    ) -> MediaAsset:
        asset = await self.repo.find_active_sticker_asset_by_id(
            db,
            asset_id=sticker_id,
        )
        if asset is None:
            raise NotFoundError(
                "Sticker not found",
                reason=ErrorReason.STICKER_NOT_FOUND,
                details={"sticker_id": sticker_id},
            )

        item = await self.repo.find_user_sticker_library_item(
            db,
            user_id=user.id,
            media_asset_id=asset.id,
        )
        if item is None:
            next_sort_order = await self.repo.get_next_user_sticker_sort_order(
                db,
                user_id=user.id,
            )
            await self.repo.create_user_sticker_library_item(
                db,
                user_id=user.id,
                media_asset_id=asset.id,
                source=StickerLibrarySource.COLLECT,
                sort_order=next_sort_order,
            )

        await db.commit()
        return asset

    async def collect_image_as_sticker(
        self,
        db: AsyncSession,
        *,
        image_id: int,
        user: User,
    ) -> MediaAsset:
        image = await self.find_media_asset_by_id(db, image_id)
        if image is None or image.asset_type != MediaAssetType.IMAGE:
            raise NotFoundError(
                "Image not found",
                reason=ErrorReason.IMAGE_NOT_FOUND,
                details={"image_id": image_id},
            )

        image = await self.expire_asset_if_needed(db, image)
        if self.is_asset_expired(image):
            raise NotFoundError(
                "Image not found",
                reason=ErrorReason.IMAGE_NOT_FOUND,
                details={"image_id": image_id},
            )

        sticker = None
        if image.sha256:
            sticker = await self.repo.find_active_media_asset_by_type_and_sha256(
                db,
                asset_type=MediaAssetType.STICKER,
                sha256=image.sha256,
            )

        if sticker is None:
            try:
                storage_key = self.storage.copy_media_file(
                    source_asset_type=MediaAssetType.IMAGE,
                    source_storage_key=image.storage_key,
                    target_asset_type=MediaAssetType.STICKER,
                )
            except FileNotFoundError as exc:
                raise NotFoundError(
                    "Media file not found",
                    reason=ErrorReason.MEDIA_FILE_NOT_FOUND,
                    details={"asset_id": image.id},
                ) from exc

            sticker = await self.repo.create_media_asset(
                db,
                asset_type=MediaAssetType.STICKER,
                storage_key=storage_key,
                mime_type=image.mime_type,
                file_size=image.file_size,
                width=image.width,
                height=image.height,
                duration_seconds=image.duration_seconds,
                sha256=image.sha256,
                uploaded_by_user_id=user.id,
                status=MediaAssetStatus.ACTIVE,
                expires_at=None,
            )

        item = await self.repo.find_user_sticker_library_item(
            db,
            user_id=user.id,
            media_asset_id=sticker.id,
        )
        if item is None:
            next_sort_order = await self.repo.get_next_user_sticker_sort_order(
                db,
                user_id=user.id,
            )
            await self.repo.create_user_sticker_library_item(
                db,
                user_id=user.id,
                media_asset_id=sticker.id,
                source=StickerLibrarySource.FROM_IMAGE,
                sort_order=next_sort_order,
            )

        await db.commit()
        return sticker

    async def get_user_sticker_library(
        self,
        db: AsyncSession,
        *,
        user: User,
        all: bool,
        page: int,
        page_size: int,
    ) -> dict[str, object]:
        
        if all:
            items = await self.repo.get_all_user_sticker_library_assets(
                db,
                user_id=user.id,
            )

            return {
                "items": items,
                "total": len(items),
                "all": True,
                "page": None,
                "page_size": None,
                "total_pages": None,
            }
        
        else:
            items, total = await self.repo.get_user_sticker_library_assets(
                db,
                user_id=user.id,
                page=page,
                page_size=page_size,
            )

            total_pages = ceil(total / page_size) if total > 0 else 0

            return {
                "items": items,
                "total": total,
                "all": False,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

    async def update_user_sticker_library(
        self,
        db: AsyncSession,
        *,
        user: User,
        sticker_ids: list[int],
    ) -> None:
        items = await self.repo.get_user_active_sticker_library_items(
            db,
            user_id=user.id,
        )

        db_id_set = set(item.media_asset_id for item in items)
        payload_id_set = set(sticker_ids)

        if len(sticker_ids) != len(payload_id_set):
            raise BadRequestError(
                "Duplicate sticker ids in library payload",
                reason=ErrorReason.DUPLICATE_STICKER_IDS,
            )

        if not payload_id_set.issubset(db_id_set):
            raise BadRequestError(
                "Sticker payload contains items not in user's sticker library",
                reason=ErrorReason.STICKER_LIBRARY_PAYLOAD_CONTAINS_INVALID_ITEMS,
            )
        
        removed_ids = list(db_id_set - payload_id_set)
        
        await self.repo.delete_user_sticker_library_items_by_asset_ids(
            db,
            user_id=user.id,
            media_asset_ids=removed_ids,
        )

        item_by_asset_id = {
            item.media_asset_id: item
            for item in items
            if item.media_asset_id in payload_id_set
        }

        total = len(sticker_ids)
        for index, asset_id in enumerate(sticker_ids):
            item_by_asset_id[asset_id].sort_order = total - index

        await db.flush()
        await db.commit()

    async def get_serving_asset(self, db: AsyncSession, asset_id: int) -> MediaAsset:
        asset = await self.get_media_asset_by_id(db, asset_id)
        asset = await self.expire_asset_if_needed(db, asset)

        if self.is_asset_expired(asset):
            raise NotFoundError(
                "Media asset not found",
                reason=ErrorReason.MEDIA_ASSET_NOT_FOUND,
                details={"asset_id": asset_id},
            )

        return asset

    async def get_user_avatar_url(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> str | None:
        asset = await self.repo.find_active_avatar_asset_by_user_id(db, user_id)
        if not asset:
            return None
        return self.get_media_asset_url(asset)

    async def get_user_avatar_storage_key(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> str | None:
        asset = await self.repo.find_active_avatar_asset_by_user_id(db, user_id)
        if not asset:
            return None
        return asset.storage_key

    async def get_user_avatar_storage_key_map(
        self,
        db: AsyncSession,
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

    def is_asset_expired(self, asset: MediaAsset, *, now: datetime | None = None) -> bool:
        now = self._normalize_datetime_to_utc_aware(now or datetime.now(timezone.utc))
        expires_at = self._normalize_datetime_to_utc_aware(asset.expires_at)

        if asset.status == MediaAssetStatus.EXPIRED:
            return True
        if asset.status == MediaAssetStatus.DELETED:
            return True
        if asset.asset_type == MediaAssetType.IMAGE and expires_at is not None:
            return expires_at <= now

        return False

    async def expire_asset_if_needed(
        self,
        db: AsyncSession,
        asset: MediaAsset,
    ) -> MediaAsset:
        if asset.asset_type != MediaAssetType.IMAGE:
            return asset

        if not self.is_asset_expired(asset):
            return asset

        if asset.status == MediaAssetStatus.ACTIVE:
            await self.repo.mark_media_assets_expired(db, asset_ids=[asset.id])
            await db.commit()
            asset.status = MediaAssetStatus.EXPIRED

        return asset

    async def cleanup_expired_images(
        self,
        db: AsyncSession,
        *,
        batch_size: int = 100,
    ) -> int:
        now = datetime.now(timezone.utc)
        assets = await self.repo.get_expired_active_image_assets(
            db,
            now=now,
            limit=batch_size,
        )
        if not assets:
            return 0

        asset_ids: list[int] = []

        for asset in assets:
            try:
                self.storage.delete_file(
                    asset_type=asset.asset_type,
                    storage_key=asset.storage_key,
                )
                asset_ids.append(asset.id)
            except FileNotFoundError:
                asset_ids.append(asset.id)
            except Exception:
                continue

        if not asset_ids:
            return 0

        await self.repo.mark_media_assets_expired(
            db,
            asset_ids=asset_ids,
        )
        await db.commit()
        return len(asset_ids)

    async def get_visible_emojis(self) -> list[dict]:
        return await self.emoji_catalog.get_visible_emojis()

    async def get_emoji(self, emoji_id: str) -> dict | None:
        return await self.emoji_catalog.get_emoji(emoji_id)

    async def get_emoji_or_raise(self, emoji_id: str) -> dict:
        emoji = await self.get_emoji(emoji_id)
        if emoji is None:
            raise BadRequestError(
                "Invalid emoji id",
                reason=ErrorReason.INVALID_EMOJI_ID,
                details={"emoji_id": emoji_id},
            )
        return emoji

    async def touch_user_emoji_usage_in_tx(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        emoji_id: str,
        provider: str = EmojiProvider.QFACE,
    ) -> None:
        # This helper participates in the caller's transaction and does not commit.
        now = datetime.now(timezone.utc)

        usage = await self.repo.find_user_emoji_usage(
            db,
            user_id=user_id,
            provider=provider,
            emoji_id=emoji_id,
        )
        if usage is None:
            await self.repo.create_user_emoji_usage(
                db,
                user_id=user_id,
                provider=provider,
                emoji_id=emoji_id,
                last_used_at=now,
            )
            return

        await self.repo.touch_user_emoji_usage_last_used_at(
            db,
            user_id=user_id,
            provider=provider,
            emoji_id=emoji_id,
            last_used_at=now,
        )

    async def get_recent_emojis(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        provider: str = EmojiProvider.QFACE,
        limit: int = 20,
    ) -> list[dict]:
        usages = await self.repo.get_recent_user_emoji_usages(
            db,
            user_id=user_id,
            provider=provider,
            limit=limit,
        )

        items: list[dict] = []
        for usage in usages:
            emoji = await self.get_emoji(usage.emoji_id)
            if emoji is None:
                continue
            items.append(emoji)

        return items

    async def validate_message_image_asset(
        self,
        db: AsyncSession,
        *,
        asset_id: int,
    ) -> MediaAsset:
        asset = await self.find_media_asset_by_id(db, asset_id)
        if asset is None or asset.asset_type != MediaAssetType.IMAGE:
            raise BadRequestError(
                "Invalid image id",
                reason=ErrorReason.INVALID_IMAGE_ID,
                details={"image_id": asset_id},
            )

        if asset.status != MediaAssetStatus.ACTIVE or self.is_asset_expired(asset):
            raise BadRequestError(
                "Image is expired or unavailable",
                reason=ErrorReason.IMAGE_UNAVAILABLE,
                details={"image_id": asset_id},
            )

        return asset
    
    async def get_user_sticker_library_item(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
    ):
        return await self.repo.find_user_sticker_library_item(
            db,
            user_id=user_id,
            media_asset_id=media_asset_id,
        )

    async def validate_message_sticker_asset(
        self,
        db: AsyncSession,
        *,
        asset_id: int,
        user_id: int,
    ) -> MediaAsset:
        asset = await self.repo.find_active_sticker_asset_by_id(
            db,
            asset_id=asset_id,
        )
        if asset is None:
            raise BadRequestError(
                "Invalid sticker id",
                reason=ErrorReason.INVALID_STICKER_ID,
                details={"sticker_id": asset_id},
            )

        item = await self.repo.find_user_sticker_library_item(
            db,
            user_id=user_id,
            media_asset_id=asset_id,
        )
        if item is None:
            raise BadRequestError(
                "Sticker is not in user's library",
                reason=ErrorReason.STICKER_NOT_IN_USER_LIBRARY,
                details={"sticker_id": asset_id},
            )

        return asset
