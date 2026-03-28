from enum import StrEnum


class WsMessageType(StrEnum):
    AUTH = "auth"
    HEARTBEAT = "heartbeat"
    COMMAND = "command"
    EVENT = "event"
    ERROR = "error"
    ACK = "ack"

class WsHeartbeatAction(StrEnum):
    PING = "ping"
    PONG = "pong"

class WsCommandAction(StrEnum):
    ROOM_ENTER = "room_enter"
    ROOM_LEAVE = "room_leave"

    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_PLAY = "playback_play"
    PLAYBACK_SEEK = "playback_seek"
    PLAYBACK_SET_SOURCE = "playback_source_set"

class WsEventType(StrEnum):
    NOTIFICATION = "notification"

    ROOM_INFO = "room_info"
    ROOM_SETTINGS = "room_settings"
    ROOM_MEMBERS = "room_members"

    MESSAGE = "message"

    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_PLAY = "playback_play"
    PLAYBACK_SEEK = "playback_seek"
    PLAYBACK_SET_SOURCE = "playback_source_set"


class WsErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    INVALID_PAYLOAD = "invalid_payload"
    INTERNAL_ERROR = "internal_error"

class ChannelKind(StrEnum):
    USER = "user"
    ROOM = "room"