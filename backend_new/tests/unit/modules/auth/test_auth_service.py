import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, decode_token
from app.modules.auth.service import AuthService


# 验证登录成功时会返回有效的 bearer token 对。
async def test_login_returns_access_and_refresh_tokens(db_session, factories) -> None:
    user = await factories.create_user(email="login@example.com", password="Password123")
    await factories.commit()

    tokens = await AuthService().login(
        db_session,
        email="login@example.com",
        password="Password123",
    )

    access_payload = decode_token(tokens["access_token"])
    refresh_payload = decode_token(tokens["refresh_token"])

    assert tokens["token_type"] == "bearer"
    assert access_payload["sub"] == str(user.id)
    assert access_payload["type"] == "access"
    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"


# 验证登录会拒绝错误密码。
async def test_login_rejects_invalid_password(db_session, factories) -> None:
    await factories.create_user(email="login@example.com", password="Password123")
    await factories.commit()

    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await AuthService().login(
            db_session,
            email="login@example.com",
            password="WrongPassword",
        )


# 验证刷新流程会拒绝非 refresh token。
async def test_refresh_tokens_rejects_non_refresh_token(db_session, factories) -> None:
    user = await factories.create_user()
    await factories.commit()

    with pytest.raises(UnauthorizedError, match="Invalid token type"):
        await AuthService().refresh_tokens(
            db_session,
            refresh_token=create_access_token(str(user.id)),
        )


# 验证刷新流程会拒绝对应用户已不存在的 token。
async def test_refresh_tokens_rejects_when_user_missing(db_session) -> None:
    with pytest.raises(UnauthorizedError, match="User not found"):
        await AuthService().refresh_tokens(
            db_session,
            refresh_token=create_access_token("999", extra={"type": "refresh"}),
        )
