from app.modules.rooms.constants import (
    RoomJoinRequestAction,
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomVisibility,
)
from app.modules.rooms.join_request.repository import RoomJoinRequestRepository
from app.modules.rooms.room.repository import RoomRepository


# 验证房间列表查询只返回公开房间，并按 id 倒序排列。
async def test_get_rooms_returns_public_rooms_in_desc_order(db_session, factories) -> None:
    owner = await factories.create_user()
    member = await factories.create_user()
    outsider = await factories.create_user()
    public_room = await factories.create_room(owner=owner, visibility=RoomVisibility.PUBLIC)
    private_owned_room = await factories.create_room(owner=member, visibility=RoomVisibility.PRIVATE)
    private_member_room = await factories.create_room(owner=owner, visibility=RoomVisibility.PRIVATE)
    hidden_room = await factories.create_room(owner=outsider, visibility=RoomVisibility.PRIVATE)
    await factories.add_member(room=private_member_room, user=member)
    await factories.commit()

    items, total = await RoomRepository().get_rooms(
        db_session,
        page=1,
        page_size=10,
    )

    assert total == 1
    assert [room.id for room in items] == [public_room.id]
    assert private_owned_room.id not in [room.id for room in items]
    assert private_member_room.id not in [room.id for room in items]
    assert hidden_room.id not in [room.id for room in items]


# 验证房间列表查询支持按名称做不区分大小写的筛选。
async def test_get_rooms_filters_by_name_case_insensitively(db_session, factories) -> None:
    owner = await factories.create_user()
    await factories.create_room(owner=owner, name="Movie Night", visibility=RoomVisibility.PUBLIC)
    await factories.create_room(owner=owner, name="Study Room", visibility=RoomVisibility.PUBLIC)
    await factories.commit()

    items, total = await RoomRepository().get_rooms(
        db_session,
        page=1,
        page_size=10,
        name="movie",
    )

    assert total == 1
    assert items[0].name == "Movie Night"


# 验证房间列表查询支持按房主用户名和邮箱做不区分大小写的筛选。
async def test_get_rooms_filters_by_owner_username_and_email(db_session, factories) -> None:
    owner_a = await factories.create_user(email="alice@example.com", username="Alice")
    owner_b = await factories.create_user(email="bob@example.com", username="Bob")
    await factories.create_room(owner=owner_a, name="Alice Public", visibility=RoomVisibility.PUBLIC)
    await factories.create_room(owner=owner_b, name="Bob Public", visibility=RoomVisibility.PUBLIC)
    await factories.create_room(owner=owner_b, name="Bob Private", visibility=RoomVisibility.PRIVATE)
    await factories.commit()

    items, total = await RoomRepository().get_rooms(
        db_session,
        page=1,
        page_size=10,
        owner_username="ali",
    )
    assert total == 1
    assert items[0].name == "Alice Public"

    items, total = await RoomRepository().get_rooms(
        db_session,
        page=1,
        page_size=10,
        owner_email="BOB@EXAMPLE",
    )
    assert total == 1
    assert items[0].name == "Bob Public"


# 验证入房申请仓储查询会按筛选条件和创建顺序返回结果。
async def test_get_join_requests_applies_filters_and_ordering(db_session, factories) -> None:
    owner = await factories.create_user()
    applicant = await factories.create_user()
    invitee = await factories.create_user()
    room = await factories.create_room(owner=owner)
    pending_request = await factories.create_join_request(
        room=room,
        initiator=applicant,
        target=applicant,
        source=RoomJoinRequestSource.APPLY,
        status=RoomJoinRequestStatus.PENDING,
        room_action=RoomJoinRequestAction.PENDING,
        target_action=RoomJoinRequestAction.APPROVED,
    )
    approved_request = await factories.create_join_request(
        room=room,
        initiator=owner,
        target=invitee,
        source=RoomJoinRequestSource.INVITE,
        status=RoomJoinRequestStatus.APPROVED,
        room_action=RoomJoinRequestAction.APPROVED,
        target_action=RoomJoinRequestAction.APPROVED,
    )
    await factories.commit()

    items, total = await RoomJoinRequestRepository().get_requests(
        db_session,
        page=1,
        page_size=10,
        room_id=room.id,
        status=RoomJoinRequestStatus.PENDING,
        source=RoomJoinRequestSource.APPLY,
    )

    assert total == 1
    assert [item.id for item in items] == [pending_request.id]
    assert approved_request.id not in [item.id for item in items]


# 验证查询待处理入房申请时只会返回目标用户在指定房间中的 pending 记录。
async def test_get_pending_request_returns_only_pending_match(db_session, factories) -> None:
    owner = await factories.create_user()
    applicant = await factories.create_user()
    room = await factories.create_room(owner=owner)
    pending_request = await factories.create_join_request(
        room=room,
        initiator=applicant,
        target=applicant,
    )
    await factories.create_join_request(
        room=room,
        initiator=owner,
        target=applicant,
        status=RoomJoinRequestStatus.APPROVED,
        room_action=RoomJoinRequestAction.APPROVED,
        target_action=RoomJoinRequestAction.APPROVED,
    )
    await factories.commit()

    found = await RoomJoinRequestRepository().get_pending_request(
        db_session,
        room_id=room.id,
        target_user_id=applicant.id,
    )

    assert found is not None
    assert found.id == pending_request.id
