from enum import StrEnum


class NotificationType(StrEnum):
    SYSTEM = "system"
    WORKFLOW = "workflow"


class NotificationRelatedType(StrEnum):
    ROOM_JOIN_REQUEST = "room_join_request"
    ANNOUNCEMENT = "announcement"