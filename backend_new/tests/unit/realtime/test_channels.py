from app.realtime.channels import ChannelKey, room_channel, user_channel
from app.realtime.constants import ChannelKind


# user_channel 会生成指向用户频道的 ChannelKey
def test_user_channel_returns_user_channel_key() -> None:
    channel = user_channel(123)

    assert channel == ChannelKey(kind=ChannelKind.USER, target_id="123")


# room_channel 会生成指向房间频道的 ChannelKey
def test_room_channel_returns_room_channel_key() -> None:
    channel = room_channel(456)

    assert channel == ChannelKey(kind=ChannelKind.ROOM, target_id="456")
