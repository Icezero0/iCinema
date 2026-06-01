from app.modules.feedback.constants import FeedbackStatus, FeedbackType
from app.modules.feedback.models import Feedback, FeedbackScreenshot
from app.modules.media.constants import MediaAssetType
from app.modules.site.constants import SiteRole
from app.modules.users.models import User


async def test_feedback_model_persists_site_role_and_feedback(db_session, factories):
    user = await factories.create_user(site_role=SiteRole.ADMIN)
    screenshot = await factories.create_media_asset(
        asset_type=MediaAssetType.FEEDBACK_IMAGE,
        uploaded_by=user,
        expires_at=None,
    )
    feedback = Feedback(
        creator_id=user.id,
        feedback_type=FeedbackType.BUG.value,
        page="room",
        title="Video does not sync",
        description="Playback position drifts after joining a room.",
        status=FeedbackStatus.OPEN.value,
    )
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)
    link = FeedbackScreenshot(feedback_id=feedback.id, asset_id=screenshot.id, sort_order=0)
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    stored_user = await db_session.get(User, user.id)

    assert stored_user is not None
    assert stored_user.site_role == SiteRole.ADMIN.value
    assert feedback.id > 0
    assert link.feedback_id == feedback.id
    assert link.asset_id == screenshot.id
    assert screenshot.asset_type == MediaAssetType.FEEDBACK_IMAGE
    assert screenshot.expires_at is None
