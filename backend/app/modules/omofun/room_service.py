import time
import uuid

from sqlalchemy import update

from app.core.exceptions import ForbiddenError
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.models import RoomSettings
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.handlers.room_video import RoomVideoCommandHandler
from .models import OmofunCache
from .service import resolve, view


async def accessible_settings(db, room_id, user_id, *, control=False):
    role = await RoomMembershipService().find_room_role(db, room_id=room_id, user_id=user_id)
    if role is None:
        raise ForbiddenError(reason="room_permission_denied")
    settings = await RoomSettingsService().get_room_settings_by_room_id(db, room_id=room_id)
    if control:
        RoomVideoCommandHandler._require_active_sync_permission(role=role, permission=settings.active_sync_permission)
    return settings


async def resolve_room(db, room_id, user_id, value, force):
    await accessible_settings(db, room_id, user_id, control=True)
    result, token = await resolve(db, value, force, user_id)
    cache = await db.get(OmofunCache, result["work_id"], populate_existing=True)
    state = {"work_id": result["work_id"], "state": result["state"], "revision": uuid.uuid4().hex,
             "token": cache.token, "baseline_version": result["version"]}
    await db.execute(update(RoomSettings).where(RoomSettings.room_id == room_id).values(omofun_resolution=state))
    await db.commit()
    return await read_room(db, room_id, user_id), token, result["work_id"]


async def read_room(db, room_id, user_id):
    settings = await accessible_settings(db, room_id, user_id)
    # Finalize pending requests from the durable cache, including after clients leave/rejoin.
    for _ in range(3):
        await db.refresh(settings)
        saved = settings.omofun_resolution
        if not saved:
            return {"state": "empty", "work_id": None, "result": None, "progress": None, "revision": None}
        cache = await db.get(OmofunCache, saved["work_id"], populate_existing=True)
        cached = view(cache, time.time()) if cache else None
        state = saved["state"]
        if state == "parsing":
            if not cached:
                state = "failed"
            elif cache.token == saved.get("token"):
                state = cached["state"]
            else:
                state = "ready" if cache.version > saved.get("baseline_version", 0) else "failed"
            if state != "parsing":
                changed = await db.execute(update(RoomSettings).where(
                    RoomSettings.room_id == room_id,
                    RoomSettings.omofun_resolution["revision"].as_string() == saved["revision"],
                ).values(omofun_resolution={**saved, "state": state}).execution_options(synchronize_session=False))
                await db.commit()
                if not changed.rowcount:
                    continue  # A newer room request won; do not publish the old result.
        if state == "ready" and (not cached or not cached["snapshot"]):
            state = "empty"
        return {"state": state, "work_id": saved["work_id"], "revision": saved["revision"],
                "result": {**cached, "state": "ready", "error": ""} if state == "ready" else None,
                "progress": cached if state == "parsing" else None}
    from app.core.exceptions import ConflictError
    raise ConflictError(reason="omofun_room_changed")
