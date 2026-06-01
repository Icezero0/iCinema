from app.core.error_reasons import ErrorReason
from app.core.exceptions import ForbiddenError
from app.modules.site.constants import SitePermission, SiteRole


ROLE_PERMISSIONS: dict[SiteRole, set[SitePermission]] = {
    SiteRole.ADMIN: {
        SitePermission.CREATE_FEEDBACK,
        SitePermission.VIEW_OWN_FEEDBACK,
        SitePermission.VIEW_ALL_FEEDBACK,
        SitePermission.UPDATE_FEEDBACK,
        SitePermission.DELETE_FEEDBACK,
    },
    SiteRole.USER: {
        SitePermission.CREATE_FEEDBACK,
        SitePermission.VIEW_OWN_FEEDBACK,
    },
}


def get_permissions_by_role(role: SiteRole) -> set[SitePermission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_site_permission(role: SiteRole, permission: SitePermission) -> bool:
    return permission in get_permissions_by_role(role)


def require_site_permission(role: SiteRole, permission: SitePermission) -> None:
    if not has_site_permission(role, permission):
        raise ForbiddenError(
            "You do not have permission to perform this action",
            reason=ErrorReason.SITE_PERMISSION_DENIED,
            details={"role": role, "permission": permission},
        )

