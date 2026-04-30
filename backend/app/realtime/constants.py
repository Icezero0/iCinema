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
    ROOM_PRESENCE_GET = "room_presence_get"
    ROOM_VIDEO_RUNTIME_GET = "room_video_runtime_get"

    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_PLAY = "playback_play"
    PLAYBACK_SEEK = "playback_seek"
    ROOM_VIDEO_SOURCE_SET = "room_video_source_set"
    USER_RESOURCE_STATUS = "user_resource_status"


class WsEventType(StrEnum):
    NOTIFICATION = "notification"

    ROOM_INFO = "room_info"
    ROOM_SETTINGS = "room_settings"
    ROOM_MEMBERS = "room_members"

    ROOM_USER_PRESENCE = "room_user_presence"
    SESSION_CLOSED = "session_closed"

    MESSAGE = "message"

    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_PLAY = "playback_play"
    PLAYBACK_SEEK = "playback_seek"
    ROOM_VIDEO_SOURCE_SET = "room_video_source_set"
    USER_RESOURCE_STATES = "user_resource_states"


class WsErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    INVALID_PAYLOAD = "invalid_payload"
    INTERNAL_ERROR = "internal_error"


class SessionCloseReason(StrEnum):
    ENTERED_ELSEWHERE = "entered_elsewhere"
    LEFT_ROOM = "left_room"
    REMOVED_FROM_ROOM = "removed_from_room"
    ROOM_DELETED = "room_deleted"


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


class ResourceHealthStatusType(StrEnum):
    READY = "ready"
    STALLING = "stalling"
    ERROR = "error"


class AutoPlaybackAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
