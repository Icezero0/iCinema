import datetime

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.constants import MediaAssetStatus, MediaAssetType
from app.modules.media.models import (
    MediaAsset,
    UserAvatarAsset,
    UserEmojiUsage,
    UserStickerLibraryItem,
)


class MediaRepository:
    async def find_media_asset_by_id(self, db: AsyncSession, asset_id: int) -> MediaAsset | None:
        result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
        return result.scalar_one_or_none()

    async def find_media_asset_by_type_and_sha256(
        self,
        db: AsyncSession,
        *,
        asset_type: str,
        sha256: str,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset)
            .where(
                MediaAsset.asset_type == asset_type,
                MediaAsset.sha256 == sha256,
            )
            .order_by(MediaAsset.id.asc())
        )
        return result.scalars().first()

    async def find_active_media_asset_by_type_and_sha256(
        self,
        db: AsyncSession,
        *,
        asset_type: str,
        sha256: str,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset)
            .where(
                MediaAsset.asset_type == asset_type,
                MediaAsset.sha256 == sha256,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(MediaAsset.id.asc())
        )
        return result.scalars().first()

    async def find_media_asset_by_type_and_storage_key(
        self,
        db: AsyncSession,
        *,
        asset_type: str,
        storage_key: str,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset).where(
                MediaAsset.asset_type == asset_type,
                MediaAsset.storage_key == storage_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_media_asset(
        self,
        db: AsyncSession,
        *,
        asset_type: str,
        storage_key: str,
        mime_type: str,
        file_size: int,
        width: int | None,
        height: int | None,
        duration_seconds: int | None,
        sha256: str | None,
        uploaded_by_user_id: int | None,
        status: str,
        expires_at,
    ) -> MediaAsset:
        asset = MediaAsset(
            asset_type=asset_type,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            sha256=sha256,
            uploaded_by_user_id=uploaded_by_user_id,
            status=status,
            expires_at=expires_at,
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        return asset

    async def touch_image_asset_expiry(
        self,
        db: AsyncSession,
        *,
        asset_id: int,
        expires_at,
    ) -> None:
        await db.execute(
            update(MediaAsset)
            .where(MediaAsset.id == asset_id)
            .values(
                status=MediaAssetStatus.ACTIVE,
                expires_at=expires_at,
            )
        )

    async def soft_delete_active_user_avatar_assets(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> None:
        await db.execute(
            update(UserAvatarAsset)
            .where(
                UserAvatarAsset.user_id == user_id,
                UserAvatarAsset.is_deleted.is_(False),
            )
            .values(is_deleted=True)
        )

    async def create_user_avatar_asset(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
    ) -> UserAvatarAsset:
        row = UserAvatarAsset(user_id=user_id, media_asset_id=media_asset_id, is_deleted=False)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def find_user_sticker_library_item(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
    ) -> UserStickerLibraryItem | None:
        result = await db.execute(
            select(UserStickerLibraryItem).where(
                UserStickerLibraryItem.user_id == user_id,
                UserStickerLibraryItem.media_asset_id == media_asset_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_next_user_sticker_sort_order(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> int:
        result = await db.execute(
            select(func.max(UserStickerLibraryItem.sort_order)).where(
                UserStickerLibraryItem.user_id == user_id
            )
        )
        current_max = result.scalar_one_or_none()
        return int(current_max or 0) + 1

    async def create_user_sticker_library_item(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
        source: str,
        sort_order: int,
    ) -> UserStickerLibraryItem:
        row = UserStickerLibraryItem(
            user_id=user_id,
            media_asset_id=media_asset_id,
            source=source,
            sort_order=sort_order,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def find_active_sticker_asset_by_id(
        self,
        db: AsyncSession,
        *,
        asset_id: int,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset).where(
                MediaAsset.id == asset_id,
                MediaAsset.asset_type == MediaAssetType.STICKER,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sticker_library_assets(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[UserStickerLibraryItem, MediaAsset]], int]:
        stmt = (
            select(UserStickerLibraryItem, MediaAsset)
            .join(
                MediaAsset,
                UserStickerLibraryItem.media_asset_id == MediaAsset.id,
            )
            .where(
                UserStickerLibraryItem.user_id == user_id,
                MediaAsset.asset_type == MediaAssetType.STICKER,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(
                UserStickerLibraryItem.sort_order.desc(),
                UserStickerLibraryItem.created_at.desc(),
                UserStickerLibraryItem.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count_stmt = (
            select(func.count())
            .select_from(UserStickerLibraryItem)
            .join(MediaAsset, UserStickerLibraryItem.media_asset_id == MediaAsset.id)
            .where(
                UserStickerLibraryItem.user_id == user_id,
                MediaAsset.asset_type == MediaAssetType.STICKER,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
        )

        result = await db.execute(stmt)
        rows = list(result.all())

        total = await db.scalar(count_stmt)
        return rows, int(total or 0)

    async def get_user_sticker_library_items_by_asset_ids(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_ids: list[int],
    ) -> list[UserStickerLibraryItem]:
        if not media_asset_ids:
            return []

        result = await db.execute(
            select(UserStickerLibraryItem).where(
                UserStickerLibraryItem.user_id == user_id,
                UserStickerLibraryItem.media_asset_id.in_(media_asset_ids),
            )
        )
        return list(result.scalars().all())
    
    async def get_user_active_sticker_library_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[UserStickerLibraryItem]:
        result = await db.execute(
            select(UserStickerLibraryItem)
            .join(MediaAsset, UserStickerLibraryItem.media_asset_id == MediaAsset.id)
            .where(
                UserStickerLibraryItem.user_id == user_id,
                MediaAsset.asset_type == MediaAssetType.STICKER,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(
                UserStickerLibraryItem.sort_order.desc(),
                UserStickerLibraryItem.created_at.desc(),
                UserStickerLibraryItem.id.desc(),
            )
        )
        return list(result.scalars().all())
    
    async def get_all_user_sticker_library_assets(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[tuple[UserStickerLibraryItem, MediaAsset]]:
        stmt = (
            select(UserStickerLibraryItem, MediaAsset)
            .join(
                MediaAsset,
                UserStickerLibraryItem.media_asset_id == MediaAsset.id,
            )
            .where(
                UserStickerLibraryItem.user_id == user_id,
                MediaAsset.asset_type == MediaAssetType.STICKER,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(
                UserStickerLibraryItem.sort_order.desc(),
                UserStickerLibraryItem.created_at.desc(),
                UserStickerLibraryItem.id.desc(),
            )
        )
        result = await db.execute(stmt)
        return list(result.all())

    async def update_user_sticker_sort_order(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
        sort_order: int,
    ) -> None:
        await db.execute(
            update(UserStickerLibraryItem)
            .where(
                UserStickerLibraryItem.user_id == user_id,
                UserStickerLibraryItem.media_asset_id == media_asset_id,
            )
            .values(sort_order=sort_order)
        )

    async def delete_user_sticker_library_items_by_asset_ids(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_ids: list[int],
    ) -> None:
        if not media_asset_ids:
            return

        await db.execute(
            delete(UserStickerLibraryItem).where(
                UserStickerLibraryItem.user_id == user_id,
                UserStickerLibraryItem.media_asset_id.in_(media_asset_ids),
            )
        )

    async def find_active_avatar_asset_by_user_id(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset)
            .join(UserAvatarAsset, UserAvatarAsset.media_asset_id == MediaAsset.id)
            .where(
                UserAvatarAsset.user_id == user_id,
                UserAvatarAsset.is_deleted.is_(False),
                MediaAsset.asset_type == MediaAssetType.AVATAR,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(UserAvatarAsset.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_active_avatar_storage_keys_by_user_ids(
        self,
        db: AsyncSession,
        user_ids: list[int],
    ) -> list[tuple[int, str]]:
        if not user_ids:
            return []

        result = await db.execute(
            select(UserAvatarAsset.user_id, MediaAsset.storage_key)
            .join(MediaAsset, UserAvatarAsset.media_asset_id == MediaAsset.id)
            .where(
                UserAvatarAsset.user_id.in_(user_ids),
                UserAvatarAsset.is_deleted.is_(False),
                MediaAsset.asset_type == MediaAssetType.AVATAR,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
            )
            .order_by(UserAvatarAsset.user_id.asc(), UserAvatarAsset.id.desc())
        )
        return list(result.all())

    async def get_media_assets_by_ids(
        self,
        db: AsyncSession,
        asset_ids: list[int],
    ) -> list[MediaAsset]:
        if not asset_ids:
            return []

        result = await db.execute(
            select(MediaAsset).where(MediaAsset.id.in_(asset_ids))
        )
        return list(result.scalars().all())

    async def get_expired_active_image_assets(
        self,
        db: AsyncSession,
        *,
        now: datetime.datetime,
        limit: int = 100,
    ) -> list[MediaAsset]:
        result = await db.execute(
            select(MediaAsset)
            .where(
                MediaAsset.asset_type == MediaAssetType.IMAGE,
                MediaAsset.status == MediaAssetStatus.ACTIVE,
                MediaAsset.expires_at.is_not(None),
                MediaAsset.expires_at <= now,
            )
            .order_by(MediaAsset.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_media_assets_expired(
        self,
        db: AsyncSession,
        *,
        asset_ids: list[int],
    ) -> None:
        if not asset_ids:
            return

        await db.execute(
            update(MediaAsset)
            .where(MediaAsset.id.in_(asset_ids))
            .values(status=MediaAssetStatus.EXPIRED)
        )

    async def find_user_emoji_usage(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        provider: str,
        emoji_id: str,
    ) -> UserEmojiUsage | None:
        result = await db.execute(
            select(UserEmojiUsage).where(
                UserEmojiUsage.user_id == user_id,
                UserEmojiUsage.provider == provider,
                UserEmojiUsage.emoji_id == emoji_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_user_emoji_usage(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        provider: str,
        emoji_id: str,
        last_used_at: datetime.datetime,
    ) -> UserEmojiUsage:
        row = UserEmojiUsage(
            user_id=user_id,
            provider=provider,
            emoji_id=emoji_id,
            last_used_at=last_used_at,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def touch_user_emoji_usage_last_used_at(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        provider: str,
        emoji_id: str,
        last_used_at: datetime.datetime,
    ) -> None:
        await db.execute(
            update(UserEmojiUsage)
            .where(
                UserEmojiUsage.user_id == user_id,
                UserEmojiUsage.provider == provider,
                UserEmojiUsage.emoji_id == emoji_id,
            )
            .values(last_used_at=last_used_at)
        )

    async def get_recent_user_emoji_usages(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        provider: str,
        limit: int = 20,
    ) -> list[UserEmojiUsage]:
        result = await db.execute(
            select(UserEmojiUsage)
            .where(
                UserEmojiUsage.user_id == user_id,
                UserEmojiUsage.provider == provider,
            )
            .order_by(desc(UserEmojiUsage.last_used_at), desc(UserEmojiUsage.id))
            .limit(limit)
        )
        return list(result.scalars().all())
