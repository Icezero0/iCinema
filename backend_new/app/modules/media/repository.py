from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.models import MediaAsset, UserAvatarAsset, UserStickerLibraryItem


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
            .values(status="active", expires_at=expires_at)
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

    async def create_user_sticker_library_item(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        media_asset_id: int,
        source: str,
    ) -> UserStickerLibraryItem:
        row = UserStickerLibraryItem(
            user_id=user_id,
            media_asset_id=media_asset_id,
            source=source,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row
    
    async def find_active_avatar_asset_by_user_id(
        self,
        db,
        user_id: int,
    ) -> MediaAsset | None:
        result = await db.execute(
            select(MediaAsset)
            .join(UserAvatarAsset, UserAvatarAsset.media_asset_id == MediaAsset.id)
            .where(
                UserAvatarAsset.user_id == user_id,
                UserAvatarAsset.is_deleted.is_(False),
                MediaAsset.asset_type == "avatar",
                MediaAsset.status == "active",
            )
            .order_by(UserAvatarAsset.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def find_active_avatar_storage_keys_by_user_ids(
        self,
        db,
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
                MediaAsset.asset_type == "avatar",
                MediaAsset.status == "active",
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