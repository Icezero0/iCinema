from app.realtime.channels import room_channel, user_channel
from app.realtime.constants import WsEventType
from app.realtime.manager import RealtimeManager
from app.realtime.protocol import build_event_message


class FakeWebSocket:
    def __init__(self, *, fail_send: bool = False) -> None:
        self.fail_send = fail_send
        self.sent_json: list[dict] = []
        self.closed = False

    async def send_json(self, payload: dict) -> None:
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent_json.append(payload)

    async def close(self) -> None:
        self.closed = True


# register_connection 会注册连接并自动订阅用户频道
async def test_register_connection_adds_connection_and_user_channel_subscription() -> None:
    manager = RealtimeManager()
    websocket = FakeWebSocket()

    connection = await manager.register_connection(
        user_id=7,
        websocket=websocket,
    )

    assert manager.connections[connection.connection_id] is connection
    assert connection.connection_id in manager.user_connections[7]
    assert user_channel(7) in connection.subscriptions
    assert connection.connection_id in manager.channel_connections[user_channel(7)]


# subscribe 和 unsubscribe 会维护连接的频道订阅关系
async def test_subscribe_and_unsubscribe_update_channel_connections() -> None:
    manager = RealtimeManager()
    connection = await manager.register_connection(
        user_id=8,
        websocket=FakeWebSocket(),
    )
    channel = room_channel(99)

    await manager.subscribe(connection_id=connection.connection_id, channel=channel)

    assert channel in connection.subscriptions
    assert connection.connection_id in manager.channel_connections[channel]

    await manager.unsubscribe(connection_id=connection.connection_id, channel=channel)

    assert channel not in connection.subscriptions
    assert channel not in manager.channel_connections


# disconnect 会清理连接、用户索引和频道索引
async def test_disconnect_cleans_all_connection_indexes() -> None:
    manager = RealtimeManager()
    connection = await manager.register_connection(
        user_id=9,
        websocket=FakeWebSocket(),
    )
    extra_channel = room_channel(100)
    await manager.subscribe(connection_id=connection.connection_id, channel=extra_channel)

    await manager.disconnect(connection.connection_id)

    assert connection.connection_id not in manager.connections
    assert 9 not in manager.user_connections
    assert extra_channel not in manager.channel_connections


# send_to_connection 在发送失败时会关闭连接并把连接移出管理器
async def test_send_to_connection_disconnects_broken_websocket() -> None:
    manager = RealtimeManager()
    websocket = FakeWebSocket(fail_send=True)
    connection = await manager.register_connection(
        user_id=10,
        websocket=websocket,
    )

    await manager.send_to_connection(
        connection_id=connection.connection_id,
        message=build_event_message(event=WsEventType.NOTIFICATION),
    )

    assert websocket.closed is True
    assert connection.connection_id not in manager.connections


# publish 会向频道内连接广播消息并尊重排除列表
async def test_publish_sends_message_to_subscribed_connections_except_excluded_ones() -> None:
    manager = RealtimeManager()
    websocket1 = FakeWebSocket()
    websocket2 = FakeWebSocket()
    connection1 = await manager.register_connection(user_id=11, websocket=websocket1)
    connection2 = await manager.register_connection(user_id=12, websocket=websocket2)
    channel = room_channel(88)

    await manager.subscribe(connection_id=connection1.connection_id, channel=channel)
    await manager.subscribe(connection_id=connection2.connection_id, channel=channel)

    await manager.publish(
        channel=channel,
        message=build_event_message(
            event=WsEventType.ROOM_USER_PRESENCE,
            data={"room_id": 88},
        ),
        exclude_connection_ids={connection2.connection_id},
    )

    assert len(websocket1.sent_json) == 1
    assert websocket2.sent_json == []
