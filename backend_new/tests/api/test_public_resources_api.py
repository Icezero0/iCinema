from datetime import datetime, timedelta, timezone

from app.modules.media.constants import MediaAssetStatus, MediaAssetType
from app.modules.media.service import MediaService


# 验证公开图片资源接口能够返回实际文件内容。
async def test_get_image_file_serves_existing_media_file(api_client, factories) -> None:
    user = await factories.create_user()
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        storage_key="served-image.png",
    )
    await factories.commit()

    path = MediaService().storage.get_file_path(
        asset_type=MediaAssetType.IMAGE,
        storage_key=asset.storage_key,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image-bytes")

    response = await api_client.get(f"/image/{asset.storage_key}")

    assert response.status_code == 200
    assert response.content == b"image-bytes"


# 验证公开图片资源接口会拒绝逻辑上已过期的图片资源。
async def test_get_image_file_rejects_expired_media_asset(api_client, factories) -> None:
    user = await factories.create_user()
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        storage_key="expired-image.png",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    await factories.commit()

    path = MediaService().storage.get_file_path(
        asset_type=MediaAssetType.IMAGE,
        storage_key=asset.storage_key,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"old-image")

    response = await api_client.get(f"/image/{asset.storage_key}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# 验证公开资源接口在文件缺失时会返回未找到错误。
async def test_get_avatar_file_rejects_missing_disk_file(api_client, factories) -> None:
    user = await factories.create_user()
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.AVATAR,
        uploaded_by=user,
        storage_key="missing-avatar.png",
    )
    await factories.commit()

    response = await api_client.get(f"/avatar/{asset.storage_key}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
