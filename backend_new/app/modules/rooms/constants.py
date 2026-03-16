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
    SET_MANAGER = "set_manager"