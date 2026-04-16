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


# 验证我的房间接口会返回我创建和加入的房间，并支持角色过滤。
async def test_get_my_rooms_returns_owned_and_joined_rooms(
    api_client,
    factories,
    auth_headers,
) -> None:
    me = await factories.create_user(username="me")
    owner = await factories.create_user(username="owner")
    owned_room = await factories.create_room(owner=me, name="Owned Room")
    joined_room = await factories.create_room(owner=owner, name="Joined Room")
    await factories.add_member(room=joined_room, user=me)
    await factories.commit()

    response = await api_client.get(
        "/api/v1/users/me/rooms",
        headers=auth_headers(me),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["name"] for item in body["items"]] == ["Joined Room", "Owned Room"]
    assert body["items"][0]["my_role"] == "member"
    assert body["items"][1]["my_role"] == "owner"
    assert body["items"][1]["owner"]["username"] == "me"

    owner_only_response = await api_client.get(
        "/api/v1/users/me/rooms?role=owner",
        headers=auth_headers(me),
    )

    assert owner_only_response.status_code == 200
    owner_body = owner_only_response.json()
    assert owner_body["total"] == 1
    assert owner_body["items"][0]["name"] == "Owned Room"


# 验证我创建的房间接口只返回当前用户创建的房间。
async def test_get_my_owned_rooms_returns_only_owned_rooms(
    api_client,
    factories,
    auth_headers,
) -> None:
    me = await factories.create_user(username="me")
    other = await factories.create_user(username="other")
    owned_room = await factories.create_room(owner=me, name="Owned Room")
    joined_room = await factories.create_room(owner=other, name="Joined Room")
    await factories.add_member(room=joined_room, user=me)
    await factories.commit()

    response = await api_client.get(
        "/api/v1/users/me/owned-rooms",
        headers=auth_headers(me),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Owned Room"
    assert body["items"][0]["my_role"] == "owner"
