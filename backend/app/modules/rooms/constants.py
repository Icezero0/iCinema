from enum import StrEnum


class RoomRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


class RoomPermission(StrEnum):
    VIEW_ROOM = "view_room"
    UPDATE_ROOM = "update_room"
    DELETE_ROOM = "delete_room"
    VIEW_MEMBERS = "view_members"
    INVITE_USER = "invite_user"
    REVIEW_JOIN_REQUEST = "review_join_request"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_MANAGERS = "manage_managers"
    VIEW_MESSAGES = "view_messages"
    SEND_MESSAGE = "send_message"


class RoomVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class RoomJoinAuditMode(StrEnum):
    AUTO_APPROVE = "auto_approve"
    MANUAL_REVIEW = "manual_review"
    AUTO_REJECT = "auto_reject"


class RoomVideoSourceType(StrEnum):
    EXTERNAL_URL = "external_url"
    LOCAL_FILE = "local_file"


class RoomSyncPolicy(StrEnum):
    AUTO_SYNC = "auto_sync"
    DISABLED = "disabled"


class RoomActiveSyncPermission(StrEnum):
    OWNER_ONLY = "owner_only"
    OWNER_AND_MANAGER = "owner_and_manager"
    ALL_MEMBERS = "all_members"


class RoomJoinRequestSource(StrEnum):
    APPLY = "apply"
    INVITE = "invite"
    MEMBER_INVITE = "member_invite"


class RoomJoinRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RoomJoinRequestAction(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RoomJoinRequestListScope(StrEnum):
    HANDLED_BY_ME = "handled_by_me"
    CREATED_BY_ME = "created_by_me"
    ALL_RELATED_TO_ME = "all_related_to_me"
