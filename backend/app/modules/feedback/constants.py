from enum import StrEnum


class FeedbackType(StrEnum):
    BUG = "bug"
    SUGGESTION = "suggestion"
    EXPERIENCE = "experience"
    OTHER = "other"


class FeedbackPage(StrEnum):
    HOME = "home"
    ROOM = "room"
    PUBLIC_ROOMS = "public_rooms"
    JOIN_REQUESTS = "join_requests"
    NOTIFICATIONS = "notifications"
    PROFILE = "profile"
    CONTACT = "contact"
    OTHER = "other"


class FeedbackStatus(StrEnum):
    OPEN = "open"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    CLOSED = "closed"

