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


# 验证 join request 列表接口支持按 scope 返回与当前用户相关的请求。
async def test_get_join_requests_lists_related_requests(
    api_client,
    factories,
    auth_headers,
) -> None:
    reviewer = await factories.create_user(username="reviewer")
    initiator = await factories.create_user(username="initiator")
    target = await factories.create_user(username="target")
    outsider = await factories.create_user(username="outsider")

    room = await factories.create_room(owner=reviewer, name="Review Room")
    other_room = await factories.create_room(owner=outsider, name="Other Room")

    visible_request = await factories.create_join_request(
        room=room,
        initiator=initiator,
        target=target,
    )
    hidden_request = await factories.create_join_request(
        room=other_room,
        initiator=outsider,
        target=target,
    )
    await factories.commit()

    response = await api_client.get(
        "/api/v1/join-requests?scope=pending_for_me",
        headers=auth_headers(reviewer),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == visible_request.id
    assert body["items"][0]["room"]["name"] == "Review Room"
    assert body["items"][0]["initiator"]["username"] == "initiator"
    assert body["items"][0]["target"]["username"] == "target"
    assert all(item["id"] != hidden_request.id for item in body["items"])


# 验证 join request 列表接口支持 created_by_me 过滤。
async def test_get_join_requests_filters_created_by_me(
    api_client,
    factories,
    auth_headers,
) -> None:
    me = await factories.create_user(username="creator")
    owner = await factories.create_user(username="owner")
    target = await factories.create_user(username="target")
    room = await factories.create_room(owner=owner, name="Target Room")
    await factories.create_join_request(room=room, initiator=me, target=target)
    await factories.create_join_request(room=room, initiator=owner, target=me)
    await factories.commit()

    response = await api_client.get(
        "/api/v1/join-requests?scope=created_by_me",
        headers=auth_headers(me),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["initiator"]["username"] == "creator"
