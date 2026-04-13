import pytest

from app.core.exceptions import ForbiddenError
from app.modules.rooms.constants import RoomPermission, RoomRole
from app.modules.rooms.permissions import has_room_permission, require_room_permission


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (RoomRole.OWNER, RoomPermission.DELETE_ROOM),
        (RoomRole.MANAGER, RoomPermission.MANAGE_MEMBERS),
        (RoomRole.MEMBER, RoomPermission.SEND_MESSAGE),
    ],
)
def test_has_room_permission_returns_true_for_allowed_combinations(
    role: RoomRole,
    permission: RoomPermission,
) -> None:
    assert has_room_permission(role, permission) is True


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (RoomRole.MANAGER, RoomPermission.DELETE_ROOM),
        (RoomRole.MEMBER, RoomPermission.REVIEW_JOIN_REQUEST),
        (RoomRole.MEMBER, RoomPermission.MANAGE_MANAGERS),
    ],
)
def test_require_room_permission_raises_for_forbidden_combinations(
    role: RoomRole,
    permission: RoomPermission,
) -> None:
    with pytest.raises(ForbiddenError):
        require_room_permission(role, permission)
