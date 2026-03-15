from enum import StrEnum


class RoomRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"