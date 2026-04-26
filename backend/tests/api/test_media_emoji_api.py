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
