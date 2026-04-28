from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token
from app.modules.auth.deps import get_current_user


def _request():
    return SimpleNamespace(state=SimpleNamespace())


# 验证鉴权依赖要求必须提供授权 token。
async def test_get_current_user_requires_token(db_session) -> None:
    with pytest.raises(UnauthorizedError, match="Missing authorization token"):
        await get_current_user(request=_request(), credentials=None, db=db_session)


# 验证鉴权依赖会拒绝在受保护接口上使用 refresh token。
async def test_get_current_user_rejects_refresh_token(db_session, factories) -> None:
    user = await factories.create_user()
    await factories.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_refresh_token(str(user.id)),
    )

    with pytest.raises(UnauthorizedError, match="Invalid token type"):
        await get_current_user(request=_request(), credentials=credentials, db=db_session)


# 验证鉴权依赖能够通过有效的 access token 解析出当前用户。
async def test_get_current_user_returns_user_for_access_token(db_session, factories) -> None:
    user = await factories.create_user()
    await factories.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_access_token(str(user.id)),
    )

    request = _request()
    resolved = await get_current_user(request=request, credentials=credentials, db=db_session)

    assert resolved.id == user.id
    assert request.state.user_id == user.id
