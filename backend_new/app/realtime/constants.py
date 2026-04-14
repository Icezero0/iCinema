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
    ROOM_VIDEO_SOURCE_SET = "room_video_source_set"
    USER_PLAYER_STATUS = "user_player_status"


class WsEventType(StrEnum):
    NOTIFICATION = "notification"

    ROOM_INFO = "room_info"
    ROOM_SETTINGS = "room_settings"
    ROOM_MEMBERS = "room_members"

    PRESENCE = "presence"
    SESSION = "session"

    MESSAGE = "message"

    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_PLAY = "playback_play"
    PLAYBACK_SEEK = "playback_seek"
    ROOM_VIDEO_SOURCE_SET = "room_video_source_set"
    USER_PLAYER_STATES = "user_player_states"


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


class PlaybackStatusType(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackHoldReason(StrEnum):
    NONE = "none"
    MANUAL = "manual"
    STALL = "stall"


class UserPlayerStatusType(StrEnum):
    READY = "ready"
    STALLING = "stalling"
    ERROR = "error"
    IDLE = "idle"


class AutoPlaybackAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
