from unittest.mock import AsyncMock

from app.modules.rooms.constants import RoomRole


# 验证通过 API 创建房间消息时会触发 realtime 广播。
async def test_create_message_publishes_realtime_event(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    owner = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.commit()

    publish_message = AsyncMock()
    app.state.realtime_publisher.publish_message = publish_message

    response = await api_client.post(
        f"/api/v1/rooms/{room.id}/messages",
        json={"content": {"segments": [{"type": "text", "text": "hello"}]}},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    publish_message.assert_awaited_once()


# 验证通过 API 全部标记通知已读时会触发 realtime 广播。
async def test_mark_all_notifications_as_read_publishes_notification_event(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    await factories.create_notification(recipient=user)
    await factories.commit()

    publish_notification = AsyncMock()
    app.state.realtime_publisher.publish_notification = publish_notification

    response = await api_client.post(
        "/api/v1/notifications/read-all",
        headers=auth_headers(user),
    )

    assert response.status_code == 204
    publish_notification.assert_awaited_once_with(user_id=user.id)


# 验证通过 API 移除房间成员后会重新广播成员列表。
async def test_remove_room_member_closes_session_and_publishes_members(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    owner = await factories.create_user()
    member = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.add_member(room=room, user=member, role=RoomRole.MEMBER)
    await factories.commit()

    app.state.realtime_publisher.publish_room_members = AsyncMock()
    app.state.realtime_room_presence_service.find_room_user_connection = AsyncMock(
        return_value=None
    )

    response = await api_client.delete(
        f"/api/v1/rooms/{room.id}/members/{member.id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 204
    app.state.realtime_publisher.publish_room_members.assert_awaited_once_with(
        room_id=room.id
    )
