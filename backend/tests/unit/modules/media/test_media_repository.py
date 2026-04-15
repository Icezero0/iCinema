from datetime import datetime, timedelta, timezone

from app.modules.media.constants import MediaAssetStatus, MediaAssetType
from app.modules.media.models import UserAvatarAsset
from app.modules.media.repository import MediaRepository


# 验证查询用户头像时会优先返回未删除且最新关联的有效头像资源。
async def test_find_active_avatar_asset_by_user_id_prefers_latest_active_avatar(
    db_session,
    factories,
) -> None:
    user = await factories.create_user()
    old_asset = await factories.create_media_asset(asset_type=MediaAssetType.AVATAR, uploaded_by=user)
    new_asset = await factories.create_media_asset(asset_type=MediaAssetType.AVATAR, uploaded_by=user)
    await factories.attach_avatar(user=user, asset=old_asset, is_deleted=False)
    await factories.attach_avatar(user=user, asset=new_asset, is_deleted=False)
    await factories.commit()

    asset = await MediaRepository().find_active_avatar_asset_by_user_id(db_session, user.id)

    assert asset is not None
    assert asset.id == new_asset.id


# 验证查询贴纸库资源时会按 sort_order 倒序返回有效贴纸。
async def test_get_user_sticker_library_assets_returns_sorted_active_stickers(
    db_session,
    factories,
) -> None:
    user = await factories.create_user()
    high = await factories.create_media_asset(asset_type=MediaAssetType.STICKER, uploaded_by=user)
    low = await factories.create_media_asset(asset_type=MediaAssetType.STICKER, uploaded_by=user)
    inactive = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
        status=MediaAssetStatus.EXPIRED,
    )
    await factories.add_sticker_to_library(user=user, asset=low, sort_order=1)
    await factories.add_sticker_to_library(user=user, asset=high, sort_order=3)
    await factories.add_sticker_to_library(user=user, asset=inactive, sort_order=5)
    await factories.commit()

    rows, total = await MediaRepository().get_user_sticker_library_assets(
        db_session,
        user_id=user.id,
        page=1,
        page_size=10,
    )

    assert total == 2
    assert [asset.id for _, asset in rows] == [high.id, low.id]


# 验证查询过期图片资源时只会返回已过期且仍处于 active 状态的图片。
async def test_get_expired_active_image_assets_returns_only_expired_active_images(
    db_session,
    factories,
) -> None:
    user = await factories.create_user()
    expired_image = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    await factories.commit()

    items = await MediaRepository().get_expired_active_image_assets(
        db_session,
        now=datetime.now(timezone.utc),
        limit=10,
    )

    assert [item.id for item in items] == [expired_image.id]
