import asyncio
import time

import pytest
from sqlalchemy import func, select, update

from app.core.database import AsyncSessionLocal
from app.core.exceptions import BadRequestError
from app.modules.catalog.models import CatalogContent
from app.modules.omofun.models import OmofunCache
from app.modules.omofun import service
from app.api.v1 import omofun as api
from app.modules.rooms.models import RoomSettings


@pytest.fixture
def upstream(monkeypatch):
    calls = []

    async def detail(path):
        calls.append(path)
        return '''<h1>Test anime</h1>
        <a class="module-play-list-link" href="/vod/play/123/ep1.html">Episode 1</a>
        <a class="module-play-list-link" href="/vod/play/123/ep2.html">Episode 2</a>'''

    async def lines(work_id, episode):
        calls.append(episode)
        return {"video_plays": [{"src_site": "jyzy", "play_data": f"https://media.example/{episode}.m3u8"}]}

    monkeypatch.setattr(service, "request_text", detail)
    monkeypatch.setattr(service, "request_lines", lines)
    return calls


@pytest.mark.asyncio
async def test_auth_cache_hit_url_normalization_and_no_catalog_writes(api_client, factories, db_session, auth_headers, upstream):
    assert (await api_client.post("/api/v1/omofun/resolve", json={"value": "123"})).status_code == 401
    user = await factories.create_user()
    await db_session.commit()
    headers = auth_headers(user)
    response = await api_client.post("/api/v1/omofun/resolve", json={"value": "123"}, headers=headers)
    assert response.status_code == 200 and response.json()["state"] == "parsing"
    result = (await api_client.get("/api/v1/omofun/123", headers=headers)).json()
    assert result["state"] == "ready" and result["version"] == 1 and not result["stale"]
    assert len(result["snapshot"]["episodes"]) == 2
    response = await api_client.post("/api/v1/omofun/resolve", json={"value": "https://omofun.in/vod/play/123"}, headers=headers)
    assert response.json()["snapshot"] == result["snapshot"] and len(upstream) == 3
    assert response.headers["cache-control"] == "no-store"
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0


@pytest.mark.asyncio
async def test_inflight_dedup_cooldown_and_admission(api_client, factories, db_session, auth_headers, monkeypatch):
    launched = []

    async def no_work(work_id, token):
        launched.append((work_id, token))

    monkeypatch.setattr(api, "run_parse", no_work)
    user = await factories.create_user()
    await db_session.commit()
    headers = auth_headers(user)
    for force in [False, True, False]:
        response = await api_client.post("/api/v1/omofun/resolve", json={"value": "123", "force": force}, headers=headers)
        assert response.status_code == 200
    assert len(launched) == 1
    busy = await api_client.post("/api/v1/omofun/resolve", json={"value": "456"}, headers=headers)
    assert busy.status_code == 429
    async with AsyncSessionLocal() as db:
        assert await db.get(OmofunCache, "456") is None


@pytest.mark.asyncio
async def test_ttl_exact_boundary_failed_refresh_preserves_snapshot(db_session, factories, upstream, monkeypatch):
    user = await factories.create_user()
    await db_session.commit()
    clock = time.time()
    user_id = user.id
    monkeypatch.setattr(service.time, "time", lambda: clock)
    _, token = await service.resolve(db_session, "123", False, user_id)
    await service.run_parse("123", token)
    db_session.expire_all()
    good = await service.read_cache(db_session, "123")
    clock += service.TTL - 1
    _, token = await service.resolve(db_session, "123", False, user_id)
    assert token is None
    clock += 1
    _, token = await service.resolve(db_session, "123", False, user_id)
    assert token

    async def broken(*args):
        raise BadRequestError(reason="omofun_no_lines")

    monkeypatch.setattr(service, "request_lines", broken)
    await service.run_parse("123", token)
    db_session.expire_all()
    failed = await service.read_cache(db_session, "123")
    assert failed["state"] == "failed" and failed["stale"]
    assert failed["snapshot"] == good["snapshot"] and failed["parsed_at"] == good["parsed_at"]
    assert failed["version"] == 1
    _, token = await service.resolve(db_session, "123", True, user_id)
    assert token is None  # Failure does not bypass refresh cooldown.


@pytest.mark.asyncio
async def test_forced_refresh_and_late_old_worker_cannot_commit(db_session, factories, upstream):
    user = await factories.create_user()
    await db_session.commit()
    user_id = user.id
    _, old_token = await service.resolve(db_session, "123", False, user_id)
    await service.run_parse("123", old_token)
    await db_session.execute(update(OmofunCache).values(attempted_at=time.time() - 61))
    await db_session.commit()
    db_session.expire_all()
    response, token = await service.resolve(db_session, "123", True, user_id)
    assert token and response["snapshot"] and response["version"] == 1
    assert not await service.write_if_owner("123", old_token, state="ready", snapshot={"wrong": True})
    await service.run_parse("123", token)
    db_session.expire_all()
    assert (await service.read_cache(db_session, "123"))["version"] == 2


@pytest.mark.asyncio
async def test_partial_first_parse_not_published_and_expired_lease_recovers(db_session, factories, upstream, monkeypatch):
    user = await factories.create_user()
    await db_session.commit()
    user_id = user.id
    original = service.request_lines

    async def partial(work, episode):
        if episode == "ep2":
            raise BadRequestError(reason="omofun_unavailable")
        return await original(work, episode)

    monkeypatch.setattr(service, "request_lines", partial)
    _, token = await service.resolve(db_session, "123", False, user_id)
    await service.run_parse("123", token)
    db_session.expire_all()
    failed = await service.read_cache(db_session, "123")
    assert failed["snapshot"] is None and failed["version"] == 0 and failed["completed"] == 1
    await db_session.execute(update(OmofunCache).values(state="parsing", lease_until=time.time()-1, attempted_at=time.time()-100))
    await db_session.commit()
    db_session.expire_all()
    assert (await service.read_cache(db_session, "123"))["error"] == "omofun_interrupted"
    _, new_token = await service.resolve(db_session, "123", False, user_id)
    assert new_token and new_token != token


@pytest.mark.asyncio
async def test_concurrent_requests_share_lease_and_global_capacity(db_session, factories):
    users = [await factories.create_user() for _ in range(3)]
    await db_session.commit()
    ids = [user.id for user in users]

    async def request(work, actor):
        async with AsyncSessionLocal() as db:
            return await service.resolve(db, work, False, actor)

    results = await asyncio.gather(request("123", ids[0]), request("123", ids[1]))
    assert sum(token is not None for _, token in results) == 1
    # Whichever user did not acquire the first lease can start the second work.
    owner_index = next(i for i, (_, token) in enumerate(results) if token)
    await request("456", ids[1 - owner_index])
    from app.core.exceptions import AppError
    with pytest.raises(AppError) as caught:
        await request("789", ids[2])
    assert caught.value.status_code == 429


@pytest.mark.asyncio
async def test_total_snapshot_limit_does_not_publish_partial_data(db_session, factories, upstream, monkeypatch):
    user = await factories.create_user()
    await db_session.commit()
    _, token = await service.resolve(db_session, "123", False, user.id)
    monkeypatch.setattr(service, "MAX_SNAPSHOT_BYTES", 1)
    await service.run_parse("123", token)
    db_session.expire_all()
    response = await service.read_cache(db_session, "123")
    assert response["state"] == "failed" and response["error"] == "omofun_limit"
    assert response["snapshot"] is None and response["parsed_at"] is None


@pytest.mark.asyncio
async def test_room_result_survives_reentry_without_selecting_playback(api_client, factories, db_session, auth_headers, upstream):
    owner = await factories.create_user()
    outsider = await factories.create_user()
    room = await factories.create_room(owner=owner)
    other_room = await factories.create_room(owner=owner)
    await db_session.commit()
    headers = auth_headers(owner)
    path = f"/api/v1/omofun/rooms/{room.id}"
    assert (await api_client.get(path, headers=headers)).json()["state"] == "empty"
    assert (await api_client.post(path + "/resolve", json={"value": "123"}, headers=headers)).json()["state"] == "parsing"
    ready = (await api_client.get(path, headers=headers)).json()
    assert ready["state"] == "ready" and ready["work_id"] == "123"
    assert ready["result"]["snapshot"]["title"] == "Test anime"
    async with AsyncSessionLocal() as fresh:
        settings = await fresh.scalar(select(RoomSettings).where(RoomSettings.room_id == room.id))
        assert settings.omofun_resolution["work_id"] == "123"
        assert settings.omofun_source is None
    assert (await api_client.get(f"/api/v1/omofun/rooms/{other_room.id}", headers=headers)).json()["state"] == "empty"
    for method, endpoint in [("get", path), ("post", path + "/resolve")]:
        kwargs = {"json": {"value": "123"}} if method == "post" else {}
        assert (await getattr(api_client, method)(endpoint, headers=auth_headers(outsider), **kwargs)).status_code == 403
    # Normal parse uses fresh successful cache even after a failed forced refresh.
    await db_session.execute(update(OmofunCache).values(state="failed", error="omofun_http", attempted_at=time.time()-61))
    await db_session.commit()
    cached = await api_client.post(path + "/resolve", json={"value": "123"}, headers=headers)
    assert cached.json()["state"] == "ready" and len(upstream) == 3
    forced = await api_client.post(path + "/resolve", json={"value": "123", "force": True}, headers=headers)
    assert forced.json()["state"] == "parsing" and len(upstream) == 6
    assert (await api_client.get(path, headers=headers)).json()["result"]["version"] == 2


@pytest.mark.asyncio
async def test_room_pending_and_failed_resolution_are_durable(api_client, factories, db_session, auth_headers, upstream, monkeypatch):
    jobs = []
    async def defer(work, token):
        jobs.append((work, token))
    monkeypatch.setattr(api, "run_parse", defer)
    owner = await factories.create_user()
    member = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.add_member(room=room, user=member)
    await db_session.commit()
    path = f"/api/v1/omofun/rooms/{room.id}"
    headers = auth_headers(owner)
    assert (await api_client.post(path + "/resolve", json={"value": "123"}, headers=auth_headers(member))).status_code == 403
    await api_client.post(path + "/resolve", json={"value": "123"}, headers=headers)
    assert (await api_client.get(path, headers=auth_headers(member))).json()["state"] == "parsing"
    async def broken(*args):
        raise BadRequestError(reason="omofun_no_lines")
    monkeypatch.setattr(service, "request_lines", broken)
    await service.run_parse(*jobs[0])
    failed = (await api_client.get(path, headers=headers)).json()
    assert failed["state"] == "failed" and failed["result"] is None
    assert (await api_client.get(path, headers=headers)).json() == failed
