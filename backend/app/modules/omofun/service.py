import asyncio
import json
import time
import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppError, NotFoundError
from .client import request_lines, request_text
from .models import OmofunCache
from .parser import normalize_work_id, parse_detail, parse_lines

TTL = 24 * 60 * 60
LEASE_SECONDS = 90
REFRESH_COOLDOWN = 60
MAX_JOB_SECONDS = 1200
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


def view(row: OmofunCache, now: float) -> dict:
    expired_job = row.state == "parsing" and row.lease_until <= now
    return {
        "work_id": row.work_id, "version": row.version, "snapshot": row.snapshot,
        "parsed_at": row.parsed_at, "expires_at": row.parsed_at + TTL if row.parsed_at else None,
        "stale": row.parsed_at is None or now >= row.parsed_at + TTL,
        "state": "failed" if expired_job else row.state,
        "error": "omofun_interrupted" if expired_job else row.error,
        "completed": row.completed, "total": row.total,
        "retry_after": max(0, int(row.attempted_at + REFRESH_COOLDOWN - now + 0.999)),
    }


async def read_cache(db, work_id: str):
    work_id = normalize_work_id(work_id)
    row = await db.get(OmofunCache, work_id)
    if row is None:
        raise NotFoundError(reason="omofun_missing")
    return view(row, time.time())


async def resolve(db, value: str, force: bool, user_id: int):
    work_id, now = normalize_work_id(value), time.time()
    row = await db.get(OmofunCache, work_id)
    if row and row.snapshot and not force and row.parsed_at is not None and now < row.parsed_at + TTL:
        # A normal parse uses the last successful cache even if another refresh failed/is running.
        return {**view(row, now), "state": "ready", "error": ""}, None
    if row and row.state == "parsing" and row.lease_until > now:
        return view(row, now), None
    if row and row.attempted_at + REFRESH_COOLDOWN > now:
        return view(row, now), None

    await db.execute(insert(OmofunCache).values(work_id=work_id).on_conflict_do_nothing())
    # SQLite serializes writers: admission and lease acquisition share this short transaction.
    active_count = select(func.count()).select_from(OmofunCache).where(
        OmofunCache.state == "parsing", OmofunCache.lease_until > now).scalar_subquery()
    user_count = select(func.count()).select_from(OmofunCache).where(
        OmofunCache.requested_by == user_id,
        or_(OmofunCache.attempted_at > now - 10,
            (OmofunCache.state == "parsing") & (OmofunCache.lease_until > now)),
    ).scalar_subquery()
    token = uuid.uuid4().hex
    result = await db.execute(update(OmofunCache).where(
        OmofunCache.work_id == work_id, OmofunCache.lease_until <= now,
        OmofunCache.attempted_at <= now - REFRESH_COOLDOWN,
        active_count < 2, user_count == 0,
    ).values(state="parsing", token=token, attempted_at=now, lease_until=now + LEASE_SECONDS,
             requested_by=user_id, error="", completed=0, total=0).execution_options(synchronize_session=False))
    if not result.rowcount:
        await db.rollback()
        db.expire_all()
        row = await db.get(OmofunCache, work_id)
        if row and row.state == "parsing" and row.lease_until > now:
            return view(row, now), None
        raise AppError("Omofun is busy, please try again shortly", status_code=429, reason="omofun_busy")
    await db.commit()
    db.expire_all()
    row = await db.get(OmofunCache, work_id)
    return view(row, now), token


async def write_if_owner(work_id, token, **values):
    async with AsyncSessionLocal() as db:
        now = time.time()
        result = await db.execute(update(OmofunCache).where(
            OmofunCache.work_id == work_id, OmofunCache.token == token,
            OmofunCache.state == "parsing", OmofunCache.lease_until > now,
        ).values(**values))
        await db.commit()
        return bool(result.rowcount)


async def run_parse(work_id: str, token: str):
    try:
        async with asyncio.timeout(MAX_JOB_SECONDS):
            snapshot = parse_detail(work_id, await request_text(f"/vod/detail/{work_id}.html"))
            total = len(snapshot["episodes"])
            snapshot_bytes = len(json.dumps(snapshot, ensure_ascii=False).encode())
            if not await write_if_owner(work_id, token, total=total, lease_until=time.time() + LEASE_SECONDS):
                return
            for completed, episode in enumerate(snapshot["episodes"], 1):
                parsed = parse_lines(await request_lines(work_id, episode["id"]))
                snapshot_bytes += len(json.dumps(parsed, ensure_ascii=False).encode())
                if snapshot_bytes > MAX_SNAPSHOT_BYTES:
                    raise AppError("Omofun snapshot too large", reason="omofun_limit")
                episode.update(parsed)
                if not await write_if_owner(work_id, token, completed=completed, lease_until=time.time() + LEASE_SECONDS):
                    return
            # Only a complete successful parse replaces the last good snapshot.
            await write_if_owner(work_id, token, snapshot=snapshot, parsed_at=time.time(),
                                 version=OmofunCache.version + 1, state="ready", error="", lease_until=0)
    except asyncio.CancelledError:
        await write_if_owner(work_id, token, state="failed", error="omofun_interrupted", lease_until=0)
        raise
    except Exception as exc:
        reason = exc.reason if isinstance(exc, AppError) else "omofun_unavailable"
        await write_if_owner(work_id, token, state="failed", error=reason, lease_until=0)
