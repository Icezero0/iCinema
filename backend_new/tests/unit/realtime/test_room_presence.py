from app.realtime.channels import room_channel
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.room_presence import RoomPresenceService


class FakeWebSocket:
    async def send_json(self, payload: dict) -> None:
        return None

    async def close(self) -> None:
        return None


async def _register_connection(manager: RealtimeManager, user_id: int) -> WsConnection:
    return await manager.register_connection(user_id=user_id, websocket=FakeWebSocket())


# enter_room 会把连接加入房间并返回包含当前用户的 presence 状态
async def test_enter_room_tracks_user_presence_and_subscribes_room_channel() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=1)

    presence = await presence_service.enter_room(
        manager=manager,
        connection=connection,
        room_id=10,
    )

    assert connection.active_room_id == 10
    assert presence.present_user_ids == [1]
    assert room_channel(10) in connection.subscriptions


# 同一个连接重复进入同一个房间时会保持幂等
async def test_enter_room_is_idempotent_for_same_connection_and_room() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=2)

    await presence_service.enter_room(manager=manager, connection=connection, room_id=20)
    presence = await presence_service.enter_room(manager=manager, connection=connection, room_id=20)

    assert presence.present_user_ids == [2]
    assert connection.active_room_id == 20


# 进入新房间时会自动从旧房间移除并更新订阅
async def test_enter_room_switches_from_previous_room() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=3)

    await presence_service.enter_room(manager=manager, connection=connection, room_id=30)
    presence = await presence_service.enter_room(manager=manager, connection=connection, room_id=31)

    assert presence.present_user_ids == [3]
    assert connection.active_room_id == 31
    assert room_channel(30) not in connection.subscriptions
    assert room_channel(31) in connection.subscriptions


# 同一用户的新连接进入同一房间时会顶掉旧连接
async def test_enter_room_replaces_old_connection_for_same_user_in_same_room() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    old_connection = await _register_connection(manager, user_id=4)
    new_connection = await _register_connection(manager, user_id=4)

    await presence_service.enter_room(manager=manager, connection=old_connection, room_id=40)
    presence = await presence_service.enter_room(manager=manager, connection=new_connection, room_id=40)

    assert presence.present_user_ids == [4]
    assert old_connection.active_room_id is None
    assert room_channel(40) not in old_connection.subscriptions
    assert new_connection.active_room_id == 40


# leave_room 在连接不在目标房间时会返回 False
async def test_leave_room_returns_false_when_connection_is_not_in_target_room() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=5)

    left = await presence_service.leave_room(
        manager=manager,
        connection=connection,
        room_id=50,
    )

    assert left is False


# leave_room 会移除 presence 映射并清理房间订阅
async def test_leave_room_removes_presence_and_room_subscription() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=6)
    await presence_service.enter_room(manager=manager, connection=connection, room_id=60)

    left = await presence_service.leave_room(
        manager=manager,
        connection=connection,
        room_id=60,
    )
    presence = await presence_service.get_presence_state(room_id=60)

    assert left is True
    assert connection.active_room_id is None
    assert presence.present_user_ids == []
    assert room_channel(60) not in connection.subscriptions


# handle_disconnect 会在断开连接时移除房间内的在线记录
async def test_handle_disconnect_removes_user_from_presence_mapping() -> None:
    manager = RealtimeManager()
    presence_service = RoomPresenceService()
    connection = await _register_connection(manager, user_id=7)
    await presence_service.enter_room(manager=manager, connection=connection, room_id=70)

    left_room_id = await presence_service.handle_disconnect(connection=connection)
    presence = await presence_service.get_presence_state(room_id=70)

    assert left_room_id == 70
    assert connection.active_room_id is None
    assert presence.present_user_ids == []
