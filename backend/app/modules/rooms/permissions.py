from app.core.error_reasons import ErrorReason
from app.core.exceptions import ForbiddenError
from app.modules.rooms.constants import RoomPermission, RoomRole

ROLE_PERMISSIONS: dict[RoomRole, set[RoomPermission]] = {
    RoomRole.OWNER: {
        RoomPermission.VIEW_ROOM,
        RoomPermission.UPDATE_ROOM,
        RoomPermission.DELETE_ROOM,
        RoomPermission.VIEW_MEMBERS,
        RoomPermission.INVITE_USER,
        RoomPermission.REVIEW_JOIN_REQUEST,
        RoomPermission.MANAGE_MEMBERS,
        RoomPermission.MANAGE_MANAGERS,
        RoomPermission.VIEW_MESSAGES,
        RoomPermission.SEND_MESSAGE,
    },
    RoomRole.MANAGER: {
        RoomPermission.UPDATE_ROOM,
        RoomPermission.VIEW_ROOM,
        RoomPermission.VIEW_MEMBERS,
        RoomPermission.INVITE_USER,
        RoomPermission.REVIEW_JOIN_REQUEST,
        RoomPermission.MANAGE_MEMBERS,
        RoomPermission.VIEW_MESSAGES,
        RoomPermission.SEND_MESSAGE,
    },
    RoomRole.MEMBER: {
        RoomPermission.VIEW_ROOM,
        RoomPermission.INVITE_USER,
        RoomPermission.VIEW_MEMBERS,
        RoomPermission.VIEW_MESSAGES,
        RoomPermission.SEND_MESSAGE,
    },
}


def get_permissions_by_role(role: RoomRole) -> set[RoomPermission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_room_permission(role: RoomRole, permission: RoomPermission) -> bool:
    return permission in get_permissions_by_role(role)


def require_room_permission(role: RoomRole, permission: RoomPermission) -> None:
    if not has_room_permission(role, permission):
        raise ForbiddenError(
            "You do not have permission to perform this action",
            reason=ErrorReason.ROOM_PERMISSION_DENIED,
            details={"role": role, "permission": permission},
        )
