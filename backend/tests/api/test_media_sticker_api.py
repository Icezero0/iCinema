from app.modules.media.constants import MediaAssetType, StickerLibrarySource
from app.modules.media.models import MediaAsset, UserStickerLibraryItem


# 验证查询全部贴纸库时会返回 all 模式响应而不带分页信息。
async def test_get_sticker_library_all_mode_returns_all_items(
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    first = await factories.create_media_asset(asset_type=MediaAssetType.STICKER, uploaded_by=user)
    second = await factories.create_media_asset(asset_type=MediaAssetType.STICKER, uploaded_by=user)
    await factories.add_sticker_to_library(user=user, asset=first, sort_order=1)
    await factories.add_sticker_to_library(user=user, asset=second, sort_order=2)
    await factories.commit()

    response = await api_client.get(
        "/api/v1/media/stickers/library?all=true",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["all"] is True
    assert body["page"] is None
    assert body["page_size"] is None
    assert body["total"] == 2


# 验证收集贴纸接口会返回贴纸信息和可访问 URL。
async def test_collect_sticker_returns_sticker_response(
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    sticker = await factories.create_media_asset(asset_type=MediaAssetType.STICKER, uploaded_by=user)
    await factories.commit()

    response = await api_client.post(
        f"/api/v1/media/stickers/{sticker.id}/collect",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sticker.id
    assert body["url"].startswith("/sticker/")


# 验证可以把已上传图片派生为贴纸并加入当前用户贴图库。
async def test_collect_image_as_sticker_creates_sticker_library_item(
    api_client,
    factories,
    auth_headers,
    sample_upload_bytes,
) -> None:
    user = await factories.create_user()
    await factories.commit()

    upload_response = await api_client.post(
        "/api/v1/media/images",
        files={"file": ("poster.png", sample_upload_bytes, "image/png")},
        headers=auth_headers(user),
    )
    image_id = upload_response.json()["id"]

    response = await api_client.post(
        f"/api/v1/media/images/{image_id}/collect-as-sticker",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] != image_id
    assert body["asset_type"] == "sticker"
    assert body["url"].startswith("/sticker/")

    items = await factories.list_all(UserStickerLibraryItem)
    assert len(items) == 1
    assert items[0].user_id == user.id
    assert items[0].media_asset_id == body["id"]
    assert items[0].source == StickerLibrarySource.FROM_IMAGE


# 验证图片内容已有对应贴纸时会复用 sticker 资源，只新增当前用户贴图库关联。
async def test_collect_image_as_sticker_reuses_existing_sticker_by_sha(
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    image = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=user,
        sha256="same-sha",
    )
    sticker = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=user,
        sha256="same-sha",
    )
    await factories.commit()

    response = await api_client.post(
        f"/api/v1/media/images/{image.id}/collect-as-sticker",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sticker.id

    assets = await factories.list_all(MediaAsset)
    stickers = [asset for asset in assets if asset.asset_type == MediaAssetType.STICKER]
    assert [asset.id for asset in stickers] == [sticker.id]

    items = await factories.list_all(UserStickerLibraryItem)
    assert len(items) == 1
    assert items[0].media_asset_id == sticker.id
    assert items[0].source == StickerLibrarySource.FROM_IMAGE
