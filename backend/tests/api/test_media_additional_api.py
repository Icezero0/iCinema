from app.modules.media.constants import MediaAssetType


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


# 验证最近表情接口会返回媒体服务提供的表情列表。
async def test_get_recent_emojis_returns_service_payload(
    api_client,
    factories,
    auth_headers,
    monkeypatch,
) -> None:
    from app.api.v1 import media as media_api

    user = await factories.create_user()
    await factories.commit()

    async def fake_get_recent_emojis(*args, **kwargs):
        return [
            {
                "provider": "qface",
                "id": "smile",
                "describe": "Smile",
                "assets": [
                    {
                        "type": 1,
                        "name": "smile",
                        "path": "/emoji/smile.png",
                        "url": "https://example.com/emoji/smile.png",
                    }
                ],
            }
        ]

    monkeypatch.setattr(media_api.media_service, "get_recent_emojis", fake_get_recent_emojis)

    response = await api_client.get(
        "/api/v1/media/emojis/recent",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "smile"
