from unittest.mock import AsyncMock

from app.modules.rooms.constants import RoomJoinAuditMode, RoomRole, RoomVisibility


# 验证房间列表接口会返回当前用户可访问的房间并支持名称筛选。
async def test_get_rooms_lists_accessible_rooms_with_name_filter(
    api_client,
    factories,
    auth_headers,
) -> None:
    user = await factories.create_user()
    await factories.create_room(owner=user, name="Movie Night")
    await factories.create_room(owner=user, name="Study Room")
    await factories.commit()

    response = await api_client.get(
        "/api/v1/rooms?name=movie",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Movie Night"


# 验证更新房间设置接口会触发 realtime 的房间设置广播。
async def test_patch_room_settings_publishes_realtime_event(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    owner = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.commit()

    app.state.realtime_publisher.publish_room_settings = AsyncMock()

    response = await api_client.patch(
        f"/api/v1/rooms/{room.id}/settings",
        json={"sync_policy": "disabled"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    app.state.realtime_publisher.publish_room_settings.assert_awaited_once_with(
        room_id=room.id
    )


# 验证自动通过的入房申请接口会直接广播房间成员列表。
async def test_apply_join_request_auto_approve_publishes_room_members(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    owner = await factories.create_user()
    applicant = await factories.create_user()
    room = await factories.create_room(
        owner=owner,
        join_audit_mode=RoomJoinAuditMode.AUTO_APPROVE,
    )
    await factories.commit()

    app.state.realtime_publisher.publish_room_members = AsyncMock()

    response = await api_client.post(
        f"/api/v1/rooms/{room.id}/join-requests/apply",
        headers=auth_headers(applicant),
    )

    assert response.status_code == 200
    app.state.realtime_publisher.publish_room_members.assert_awaited_once_with(
        room_id=room.id
    )


# 验证普通成员发起邀请时，会通知目标用户以及房间审核人。
async def test_invite_join_request_notifies_target_and_reviewers(
    app,
    api_client,
    factories,
    auth_headers,
) -> None:
    owner = await factories.create_user()
    member = await factories.create_user()
    target = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.add_member(room=room, user=member, role=RoomRole.MEMBER)
    await factories.commit()

    publish_notification = AsyncMock()
    app.state.realtime_publisher.publish_notification = publish_notification

    response = await api_client.post(
        f"/api/v1/rooms/{room.id}/join-requests/invite",
        json={"target_user_id": target.id},
        headers=auth_headers(member),
    )

    assert response.status_code == 200
    notified_user_ids = [call.kwargs["user_id"] for call in publish_notification.await_args_list]
    assert notified_user_ids == [target.id, owner.id]
