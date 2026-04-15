from __future__ import annotations

from dataclasses import dataclass

from app.realtime.constants import ChannelKind


@dataclass(frozen=True, slots=True)
class ChannelKey:
    kind: ChannelKind
    target_id: str


def user_channel(user_id: int) -> ChannelKey:
    return ChannelKey(kind=ChannelKind.USER, target_id=str(user_id))


def room_channel(room_id: int) -> ChannelKey:
    return ChannelKey(kind=ChannelKind.ROOM, target_id=str(room_id))