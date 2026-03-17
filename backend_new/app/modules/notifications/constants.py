from enum import StrEnum


class NotificationType(StrEnum):
    SYSTEM = "system"
    WORKFLOW = "workflow"


class NotificationRelatedType(StrEnum):
    ROOM_MEMBERSHIP_REQUEST = "room_membership_request"