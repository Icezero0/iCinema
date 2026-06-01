from app.modules.feedback.constants import FeedbackPage, FeedbackStatus, FeedbackType
from app.modules.media.constants import MediaAssetType
from app.modules.media.models import MediaAsset
from app.modules.site.constants import SiteRole


async def test_create_feedback_with_screenshots(api_client, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()

    response = await api_client.post(
        "/api/v1/feedback",
        data={
            "feedback_type": FeedbackType.BUG.value,
            "page": FeedbackPage.ROOM.value,
            "title": "Player desync",
            "description": "Playback position drifts after joining.",
        },
        files=[
            ("screenshots", ("screen-1.png", b"fake-image-1", "image/png")),
            ("screenshots", ("screen-2.webp", b"fake-image-2", "image/webp")),
        ],
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["creator_id"] == user.id
    assert body["feedback_type"] == "bug"
    assert body["page"] == "room"
    assert body["status"] == "open"
    assert len(body["screenshot_asset_ids"]) == 2
    assert len(body["screenshot_urls"]) == 2
    assert body["screenshot_urls"][0].endswith(f"/feedback/assets/{body['screenshot_asset_ids'][0]}")

    assets = await factories.list_all(MediaAsset)
    feedback_assets = [asset for asset in assets if asset.asset_type == MediaAssetType.FEEDBACK_IMAGE]
    assert len(feedback_assets) == 2
    assert feedback_assets[0].expires_at is None


async def test_user_can_list_and_view_own_feedback(api_client, factories, auth_headers):
    user = await factories.create_user()
    other = await factories.create_user()
    own = await factories.create_feedback(creator=user, title="Mine")
    await factories.create_feedback(creator=other, title="Other")
    await factories.commit()

    list_response = await api_client.get("/api/v1/feedback", headers=auth_headers(user))

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == own.id

    detail_response = await api_client.get(f"/api/v1/feedback/{own.id}", headers=auth_headers(user))

    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Mine"


async def test_user_cannot_view_other_feedback(api_client, factories, auth_headers):
    user = await factories.create_user()
    other = await factories.create_user()
    feedback = await factories.create_feedback(creator=other)
    await factories.commit()

    response = await api_client.get(f"/api/v1/feedback/{feedback.id}", headers=auth_headers(user))

    assert response.status_code == 403
    assert response.json()["error"]["reason"] == "feedback_permission_denied"


async def test_admin_can_list_and_update_feedback(api_client, factories, auth_headers):
    user = await factories.create_user()
    admin = await factories.create_user(site_role=SiteRole.ADMIN)
    feedback = await factories.create_feedback(creator=user)
    await factories.commit()

    list_response = await api_client.get("/api/v1/feedback/admin", headers=auth_headers(admin))

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = await api_client.patch(
        f"/api/v1/feedback/admin/{feedback.id}",
        json={"status": FeedbackStatus.REVIEWING.value, "admin_note": "Checking"},
        headers=auth_headers(admin),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "reviewing"
    assert body["admin_note"] == "Checking"
    assert body["handled_by_id"] == admin.id


async def test_non_admin_cannot_access_feedback_admin_api(api_client, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()

    response = await api_client.get("/api/v1/feedback/admin", headers=auth_headers(user))

    assert response.status_code == 403
    assert response.json()["error"]["reason"] == "site_permission_denied"


async def test_feedback_screenshot_access_is_limited(
    api_client,
    factories,
    auth_headers,
):
    owner = await factories.create_user()
    other = await factories.create_user()
    admin = await factories.create_user(site_role=SiteRole.ADMIN)
    asset = await factories.create_media_asset(
        asset_type=MediaAssetType.FEEDBACK_IMAGE,
        uploaded_by=owner,
        storage_key="feedback-test.png",
    )
    await factories.create_feedback(creator=owner, screenshot_assets=[asset])
    await factories.commit()

    from app.core.config import get_settings

    path = get_settings().feedback_image_dir_path / asset.storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"feedback-screen")

    owner_response = await api_client.get(
        f"/api/v1/feedback/assets/{asset.id}",
        headers=auth_headers(owner),
    )
    other_response = await api_client.get(
        f"/api/v1/feedback/assets/{asset.id}",
        headers=auth_headers(other),
    )
    admin_response = await api_client.get(
        f"/api/v1/feedback/assets/{asset.id}",
        headers=auth_headers(admin),
    )

    assert owner_response.status_code == 200
    assert owner_response.content == b"feedback-screen"
    assert other_response.status_code == 403
    assert admin_response.status_code == 200

    if path.exists():
        path.unlink()


async def test_feedback_screenshot_access_returns_requested_asset(
    api_client,
    factories,
    auth_headers,
):
    owner = await factories.create_user()
    first_asset = await factories.create_media_asset(
        asset_type=MediaAssetType.FEEDBACK_IMAGE,
        uploaded_by=owner,
        storage_key="feedback-first.png",
    )
    second_asset = await factories.create_media_asset(
        asset_type=MediaAssetType.FEEDBACK_IMAGE,
        uploaded_by=owner,
        storage_key="feedback-second.png",
    )
    await factories.create_feedback(
        creator=owner,
        screenshot_assets=[first_asset, second_asset],
    )
    await factories.commit()

    from app.core.config import get_settings

    base_path = get_settings().feedback_image_dir_path
    first_path = base_path / first_asset.storage_key
    second_path = base_path / second_asset.storage_key
    first_path.parent.mkdir(parents=True, exist_ok=True)
    first_path.write_bytes(b"first-feedback-screen")
    second_path.write_bytes(b"second-feedback-screen")

    first_response = await api_client.get(
        f"/api/v1/feedback/assets/{first_asset.id}",
        headers=auth_headers(owner),
    )
    second_response = await api_client.get(
        f"/api/v1/feedback/assets/{second_asset.id}",
        headers=auth_headers(owner),
    )

    assert first_response.status_code == 200
    assert first_response.content == b"first-feedback-screen"
    assert second_response.status_code == 200
    assert second_response.content == b"second-feedback-screen"

    for path in (first_path, second_path):
        if path.exists():
            path.unlink()


async def test_feedback_rejects_too_many_screenshots(api_client, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()

    response = await api_client.post(
        "/api/v1/feedback",
        data={
            "feedback_type": FeedbackType.BUG.value,
            "page": FeedbackPage.ROOM.value,
            "title": "Many screenshots",
            "description": "This should be rejected.",
        },
        files=[
            ("screenshots", (f"screen-{index}.png", b"fake-image", "image/png"))
            for index in range(7)
        ],
        headers=auth_headers(user),
    )

    assert response.status_code == 400
