import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import verify_password
from app.modules.users.schemas import UserCreate, UserPatch
from app.modules.users.service import UserService


# 验证创建用户时会规范化邮箱并存储哈希后的密码。
async def test_create_user_hashes_password_and_normalizes_email(db_session) -> None:
    service = UserService()

    user = await service.create_user(
        db_session,
        UserCreate(
            email="  NEW@Example.com ",
            username="Alice",
            password="Password123",
        ),
    )

    assert user.email == "new@example.com"
    assert verify_password("Password123", user.hashed_password) is True


# 验证创建用户时会拒绝重复邮箱。
async def test_create_user_rejects_duplicate_email(db_session, factories) -> None:
    await factories.create_user(email="taken@example.com")
    await factories.commit()

    with pytest.raises(ConflictError, match="Email already exists"):
        await UserService().create_user(
            db_session,
            UserCreate(
                email="taken@example.com",
                username="Bob",
                password="Password123",
            ),
        )


# 验证查询不存在的用户时会抛出未找到错误。
async def test_get_user_by_id_raises_for_missing_user(db_session) -> None:
    with pytest.raises(NotFoundError, match="User not found"):
        await UserService().get_user_by_id(db_session, 999)


# 验证更新当前用户时只会修改传入的字段。
async def test_patch_me_updates_selected_fields(db_session, factories) -> None:
    user = await factories.create_user(username="before", password="Password123")
    await factories.commit()

    updated = await UserService().patch_me(
        db_session,
        user,
        UserPatch(username="after", password="NewPassword123", auto_accept=True),
    )

    assert updated.username == "after"
    assert updated.auto_accept is True
    assert verify_password("NewPassword123", updated.hashed_password) is True
