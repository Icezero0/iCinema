from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.exceptions import BadRequestError, NotFoundError
from app.modules.media.constants import MediaAssetStatus, MediaAssetType
from app.modules.media.models import UserStickerLibraryItem
from app.modules.media.service import MediaService


# 验证重复图片上传会复用已有资源并刷新过期时间。
async def test_create_image_asset_reuses_sha_and_refreshes_expiry(
    db_session,
    factories,
    monkeypatch,
) -> None:
    user = await factories.create_user()
    existing = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        sha256="dup-sha",
    )
    old_expiry = datetime.now(timezone.utc) - timedelta(days=1)
    existing.expires_at = old_expiry
    await factories.commit()

    service = MediaService()

    async def fake_prepare_upload(**kwargs):
        return SimpleNamespace(
            sha256="dup-sha",
            mime_type="image/png",
            file_size=32,
            width=None,
            height=None,
            duration_seconds=None,
            ext=".png",
            content=b"png",
        )

    monkeypatch.setattr(service.storage, "prepare_upload", fake_prepare_upload)

    asset = await service.create_image_asset(
        db_session,
        file=SimpleNamespace(),
        user=user,
    )

    assert asset.id == existing.id
    assert asset.expires_at is not None
    assert (
        service._normalize_datetime_to_utc_aware(asset.expires_at)
        > service._normalize_datetime_to_utc_aware(old_expiry)
    )


# 验证更新贴纸库时会重排保留项并删除被移除的项。
async def test_update_user_sticker_library_reorders_and_removes_missing_items(
    db_session,
    factories,
) -> None:
    user = await factories.create_user()
    first = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
    )
    second = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
    )
    third = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
    )
    await factories.add_sticker_to_library(user=user, asset=first, sort_order=3)
    await factories.add_sticker_to_library(user=user, asset=second, sort_order=2)
    await factories.add_sticker_to_library(user=user, asset=third, sort_order=1)
    await factories.commit()

    await MediaService().update_user_sticker_library(
        db_session,
        user=user,
        sticker_ids=[third.id, first.id],
    )

    items = await factories.list_all(UserStickerLibraryItem)
    by_asset_id = {item.media_asset_id: item for item in items}

    assert set(by_asset_id) == {first.id, third.id}
    assert by_asset_id[third.id].sort_order == 2
    assert by_asset_id[first.id].sort_order == 1


# 验证消息贴纸校验要求贴纸必须存在于用户贴纸库中。
async def test_validate_message_sticker_asset_requires_library_membership(
    db_session,
    factories,
) -> None:
    user = await factories.create_user()
    sticker = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
    )
    await factories.commit()

    with pytest.raises(BadRequestError, match="Sticker is not in user's library"):
        await MediaService().validate_message_sticker_asset(
            db_session,
            asset_id=sticker.id,
            user_id=user.id,
        )


# 验证图片资源在惰性过期流程中会被标记为已过期。
async def test_expire_asset_if_needed_marks_expired_image(db_session, factories) -> None:
    user = await factories.create_user()
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    await factories.commit()

    updated = await MediaService().expire_asset_if_needed(db_session, asset)

    assert updated.status == MediaAssetStatus.EXPIRED


# 验证访问已过期资源时会返回未找到错误。
async def test_get_serving_asset_rejects_expired_asset(db_session, factories) -> None:
    user = await factories.create_user()
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        status=MediaAssetStatus.EXPIRED,
    )
    await factories.commit()

    with pytest.raises(NotFoundError, match="Media asset not found"):
        await MediaService().get_serving_asset(db_session, asset.id)
