from app.modules.notifications.constants import NotificationType
from app.modules.notifications.repository import NotificationRepository


# 验证通知仓储查询会按已读状态和类型筛选，并按最新记录优先返回。
async def test_get_notifications_filters_and_orders_results(db_session, factories) -> None:
    user = await factories.create_user()
    actor = await factories.create_user()
    first = await factories.create_notification(
        recipient=user,
        actor=actor,
        notification_type=NotificationType.WORKFLOW,
    )
    second = await factories.create_notification(
        recipient=user,
        actor=actor,
        notification_type=NotificationType.SYSTEM,
        is_read=True,
    )
    await factories.commit()

    items, total = await NotificationRepository().get_notifications(
        db_session,
        recipient_user_id=user.id,
        page=1,
        page_size=10,
        is_read=False,
        notification_type=NotificationType.WORKFLOW.value,
    )

    assert total == 1
    assert [item.id for item in items] == [first.id]
    assert second.id not in [item.id for item in items]


# 验证批量标记已读只会更新当前用户未读的通知。
async def test_mark_all_as_read_updates_only_unread_notifications(db_session, factories) -> None:
    user = await factories.create_user()
    other = await factories.create_user()
    own_unread = await factories.create_notification(recipient=user, is_read=False)
    own_read = await factories.create_notification(recipient=user, is_read=True)
    other_unread = await factories.create_notification(recipient=other, is_read=False)
    await factories.commit()

    await NotificationRepository().mark_all_as_read(
        db_session,
        recipient_user_id=user.id,
    )
    await factories.commit()

    await factories.refresh(own_unread)
    await factories.refresh(own_read)
    await factories.refresh(other_unread)

    assert own_unread.is_read is True
    assert own_unread.read_at is not None
    assert own_read.is_read is True
    assert other_unread.is_read is False
