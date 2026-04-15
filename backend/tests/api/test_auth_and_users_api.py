# 验证注册、登录、刷新 token 与获取当前用户接口能够串联工作。
async def test_register_login_refresh_and_get_me_flow(api_client) -> None:
    register_response = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "api-user@example.com",
            "username": "api-user",
            "password": "Password123",
        },
    )

    assert register_response.status_code == 201
    created_user = register_response.json()
    assert created_user["email"] == "api-user@example.com"

    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "api-user@example.com", "password": "Password123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"

    refresh_response = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200

    me_response = await api_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "api-user@example.com"


# 验证获取当前用户接口会拒绝匿名访问。
async def test_get_me_requires_authentication(api_client) -> None:
    response = await api_client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# 验证通过 API 更新当前用户时会持久化资料变更。
async def test_patch_me_updates_user_profile(api_client, factories, auth_headers) -> None:
    user = await factories.create_user(username="before")
    await factories.commit()

    response = await api_client.patch(
        "/api/v1/users/me",
        json={"username": "after", "auto_accept": True},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["username"] == "after"
    assert response.json()["auto_accept"] is True
