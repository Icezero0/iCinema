import pytest

from app.core.exceptions import ForbiddenError
from app.modules.site.constants import SitePermission, SiteRole
from app.modules.site.permissions import (
    get_permissions_by_role,
    has_site_permission,
    require_site_permission,
)


def test_site_admin_has_all_feedback_permissions():
    permissions = get_permissions_by_role(SiteRole.ADMIN)

    assert SitePermission.CREATE_FEEDBACK in permissions
    assert SitePermission.VIEW_OWN_FEEDBACK in permissions
    assert SitePermission.VIEW_ALL_FEEDBACK in permissions
    assert SitePermission.UPDATE_FEEDBACK in permissions
    assert SitePermission.DELETE_FEEDBACK in permissions


def test_site_user_only_has_self_service_feedback_permissions():
    permissions = get_permissions_by_role(SiteRole.USER)

    assert permissions == {
        SitePermission.CREATE_FEEDBACK,
        SitePermission.VIEW_OWN_FEEDBACK,
    }
    assert not has_site_permission(SiteRole.USER, SitePermission.VIEW_ALL_FEEDBACK)


def test_require_site_permission_raises_for_missing_permission():
    with pytest.raises(ForbiddenError):
        require_site_permission(SiteRole.USER, SitePermission.UPDATE_FEEDBACK)

