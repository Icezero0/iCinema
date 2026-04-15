import pytest

from app.core.exceptions import ForbiddenError
from app.modules.notifications.constants import NotificationType
from app.modules.notifications.service import NotificationService


# 验证只有通知接收者才能按 id 获取通知。
async def test_get_notification_by_id_rejects_non_recipient(db_session, factories) -> None:
    recipient = await factories.create_user()
    other = await factories.create_user()
    notification = await factories.create_notification(recipient=recipient)
    await factories.commit()

    with pytest.raises(ForbiddenError, match="You do not have permission"):
        await NotificationService().get_notification_by_id(
            db_session,
            notification_id=notification.id,
            user=other,
        )


# 验证标记通知已读时会更新已读状态和时间。
async def test_mark_as_read_sets_read_flag_once(db_session, factories) -> None:
    recipient = await factories.create_user()
    notification = await factories.create_notification(
        recipient=recipient,
        notification_type=NotificationType.SYSTEM,
    )
    await factories.commit()

    updated = await NotificationService().mark_as_read(
        db_session,
        notification_id=notification.id,
        user=recipient,
    )

    assert updated.is_read is True
    assert updated.read_at is not None


# 验证通知列表能够正确应用已读状态和类型筛选。
async def test_get_notifications_returns_filtered_page(db_session, factories) -> None:
    recipient = await factories.create_user()
    await factories.create_notification(
        recipient=recipient,
        notification_type=NotificationType.WORKFLOW,
    )
    await factories.create_notification(
        recipient=recipient,
        notification_type=NotificationType.SYSTEM,
        is_read=True,
    )
    await factories.commit()

    data = await NotificationService().get_notifications(
        db_session,
        user=recipient,
        page=1,
        page_size=10,
        is_read=False,
        notification_type=NotificationType.WORKFLOW,
    )

    assert data["total"] == 1
    assert data["items"][0].notification_type == NotificationType.WORKFLOW
