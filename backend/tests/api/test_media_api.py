# 验证上传图片后会返回可访问的公开图片 URL。
async def test_upload_image_returns_public_url(
    api_client,
    factories,
    auth_headers,
    sample_upload_bytes,
) -> None:
    user = await factories.create_user()
    await factories.commit()

    response = await api_client.post(
        "/api/v1/media/images",
        files={"file": ("poster.png", sample_upload_bytes, "image/png")},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["asset_type"] == "image"
    assert body["url"].startswith("/image/")


# 验证查询贴纸库时，当 all=true 会拒绝同时传入分页参数。
async def test_get_sticker_library_rejects_page_params_when_all_true(
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    await factories.commit()

    response = await api_client.get(
        "/api/v1/media/stickers/library?all=true&page=1&page_size=20",
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
