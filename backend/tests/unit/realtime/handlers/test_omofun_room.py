from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError
from app.modules.omofun.models import OmofunCache
from app.modules.rooms.constants import RoomSyncPolicy, RoomVideoSourceType
from app.modules.rooms.models import RoomSettings
from app.realtime.constants import WsCommandAction
from app.realtime.handlers.room import RoomCommandHandler
from app.realtime.handlers.room_video import RoomVideoCommandHandler
from app.realtime.manager import WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.room_video_runtime import RoomVideoRuntimeService
from app.realtime.state import PresenceState


def command(**changes):
    return WsCommandPayload(request_id="omofun-pick", action=WsCommandAction.ROOM_VIDEO_SOURCE_SET,
        data={"source_type": "omofun", "work_id": "123", "episode_id": "ep1", "line_id": "line1",
              "cache_version": 1, "expected_source_revision": 0, **changes})


def publisher():
    return SimpleNamespace(**{key: AsyncMock() for key in ["publish_room_video_source_set", "publish_playback_pause",
        "publish_user_resource_states", "publish_room_user_presence", "publish_session_closed"]})


@pytest.fixture
async def context(db_session, factories):
    owner = await factories.create_user()
    member = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.add_member(room=room, user=member)
    cache = OmofunCache(work_id="123", state="ready", version=1, snapshot={"title": "Test work", "episodes": [
        {"id": "ep1", "title": "Episode 1", "lines": [{"id": "line1", "source": "jyzy", "url": "https://media.example/old.m3u8"}]}]})
    db_session.add(cache)
    await db_session.commit()
    runtime = RoomVideoRuntimeService()
    return SimpleNamespace(owner_id=owner.id, member_id=member.id, room_id=room.id, cache=cache,
        runtime=runtime, handler=RoomVideoCommandHandler(runtime), publisher=publisher())


async def apply(ctx, db, payload=None, user_id=None):
    return await ctx.handler.handle(db=db, manager=object(), publisher=ctx.publisher,
        connection=WsConnection(connection_id="pick", user_id=user_id or ctx.owner_id,
            websocket=SimpleNamespace(), active_room_id=ctx.room_id), command=payload or command())


@pytest.mark.asyncio
async def test_selection_uses_server_url_and_persists_pin(context, db_session):
    ctx = context
    response = await apply(ctx, db_session)
    source = response["room_video_source"]
    assert source["source_type"] == "omofun" and source["external_url"].endswith("old.m3u8")
    assert source["source_revision"] == 1 and source["omofun"]["work_id"] == "123"
    assert response["playback"]["status"] == "paused" and response["playback"]["position_seconds"] == 0
    settings = await db_session.scalar(select(RoomSettings).where(RoomSettings.room_id == ctx.room_id))
    assert settings.selected_room_video_source_type == "omofun"
    assert settings.omofun_source["external_url"] == source["external_url"]
    ctx.publisher.publish_room_video_source_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_refresh_does_not_change_active_room_or_join_snapshot(context, db_session):
    ctx = context
    await apply(ctx, db_session)
    await ctx.runtime.play(room_id=ctx.room_id, position_seconds=42, anchor_ts_ms=1000,
                           sync_policy=RoomSyncPolicy.DISABLED)
    before = await ctx.runtime.get_playback(room_id=ctx.room_id)
    ctx.cache.version = 2
    ctx.cache.snapshot = {"title": "Updated", "episodes": [{"id": "ep1", "title": "Episode 1", "lines": [
        {"id": "line2", "source": "jyzy", "url": "https://media.example/new.m3u8"}]}]}
    await db_session.commit()
    assert (await ctx.runtime.get_playback(room_id=ctx.room_id)) == before
    presence = SimpleNamespace(find_room_user_connection=AsyncMock(return_value=None),
        enter_room=AsyncMock(return_value=PresenceState(room_id=ctx.room_id, present_user_ids=[ctx.member_id])))
    join = RoomCommandHandler(presence, ctx.runtime)
    response = await join.handle(db=db_session, manager=object(), publisher=ctx.publisher,
        connection=WsConnection(connection_id="join", user_id=ctx.member_id, websocket=SimpleNamespace()),
        command=WsCommandPayload(request_id="join", action=WsCommandAction.ROOM_ENTER, data={"room_id": ctx.room_id}))
    assert response["room_video_source"]["external_url"].endswith("old.m3u8")
    assert response["playback"]["status"] == "playing"
    assert response["playback"]["position_seconds"] == 42
    response = await apply(ctx, db_session, command(cache_version=2, line_id="line2", expected_source_revision=1))
    assert response["room_video_source"]["external_url"].endswith("new.m3u8")


@pytest.mark.asyncio
async def test_restart_restores_pinned_selection_paused_not_latest_cache(context, db_session):
    ctx = context
    await apply(ctx, db_session)
    ctx.cache.snapshot = None
    await db_session.commit()
    runtime = RoomVideoRuntimeService()
    presence = SimpleNamespace(find_room_user_connection=AsyncMock(return_value=None),
        enter_room=AsyncMock(return_value=PresenceState(room_id=ctx.room_id, present_user_ids=[ctx.owner_id])))
    join = RoomCommandHandler(presence, runtime)
    response = await join.handle(db=db_session, manager=object(), publisher=ctx.publisher,
        connection=WsConnection(connection_id="restart", user_id=ctx.owner_id, websocket=SimpleNamespace()),
        command=WsCommandPayload(request_id="enter", action=WsCommandAction.ROOM_ENTER, data={"room_id": ctx.room_id}))
    assert response["room_video_source"]["external_url"].endswith("old.m3u8")
    assert response["room_video_source"]["source_revision"] == 1
    assert response["playback"]["status"] == "paused"


@pytest.mark.asyncio
@pytest.mark.parametrize("changes,error", [({"external_url": "https://evil.example/test.m3u8"}, BadRequestError),
    ({"cache_version": 99}, ConflictError), ({"line_id": "missing"}, BadRequestError),
    ({"expected_source_revision": 99}, ConflictError)])
async def test_invalid_or_stale_selection_cannot_mutate_room(context, db_session, changes, error):
    with pytest.raises(error):
        await apply(context, db_session, command(**changes))
    assert await context.runtime.get_room_video_source(room_id=context.room_id) is None
    context.publisher.publish_room_video_source_set.assert_not_awaited()


@pytest.mark.asyncio
async def test_member_cannot_change_source_and_old_selection_rejected_after_external_switch(context, db_session):
    ctx = context
    with pytest.raises(ForbiddenError):
        await apply(ctx, db_session, user_id=ctx.member_id)
    await apply(ctx, db_session)
    await apply(ctx, db_session, WsCommandPayload(request_id="external", action=WsCommandAction.ROOM_VIDEO_SOURCE_SET,
        data={"source_type": "external_url", "external_url": "https://media.example/manual.m3u8"}))
    with pytest.raises(ConflictError):
        await apply(ctx, db_session, command(expected_source_revision=1))
    settings = await db_session.scalar(select(RoomSettings).where(RoomSettings.room_id == ctx.room_id))
    assert settings.omofun_source is None and settings.selected_room_video_source_type == "external_url"
