import asyncio
import logging
from datetime import datetime, timezone
from math import ceil
import time
import uuid

from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppError, BadRequestError, ConflictError, NotFoundError
from . import provider_client
from .import_models import CatalogProvider, CatalogImportJob, CatalogSource
from .import_parser import parse_detail, plain
from .import_sync import sync_work
from .service import CatalogService

LEASE_SECONDS = 180
SUCCESS = {"created", "updated", "unchanged", "skipped"}


async def get_provider(db, provider_id, require_enabled=False):
    provider = await db.get(CatalogProvider, provider_id)
    if provider is None:
        raise NotFoundError("Provider not found", reason="catalog_provider_missing")
    if require_enabled and not provider.enabled:
        raise BadRequestError("Provider disabled", reason="catalog_provider_disabled")
    return provider


async def get_job(db, job_id):
    job = await db.get(CatalogImportJob, job_id)
    if job is None:
        raise NotFoundError("Import not found", reason="catalog_import_missing")
    return job


async def recover_expired(db):
    await db.execute(update(CatalogImportJob).where(
        CatalogImportJob.status.in_(["queued", "running"]), CatalogImportJob.lease_until < time.time(),
    ).values(status="interrupted", lease_token="", updated_at=func.now()))
    await db.commit()


async def save_provider(db, provider_id, payload):
    await get_provider(db, provider_id)
    await CatalogService().require_category(db, payload.category)
    result = await db.execute(update(CatalogProvider).where(
        CatalogProvider.id == provider_id, CatalogProvider.version == payload.version,
    ).values(**payload.model_dump(exclude={"version"}), version=payload.version + 1))
    if not result.rowcount:
        await db.rollback()
        raise ConflictError("Provider changed", reason="catalog_version_conflict")
    await db.commit()
    db.expire_all()
    return await get_provider(db, provider_id)


async def create_provider(db, payload):
    await CatalogService().require_category(db, payload.category)
    provider = CatalogProvider(**payload.model_dump())
    db.add(provider)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Provider code already exists", reason="catalog_provider_duplicate") from exc
    await db.refresh(provider)
    return provider


async def check_provider(db, provider_id):
    provider = await get_provider(db, provider_id, True)
    data = await provider_client.request_json(provider.id, provider.endpoint, dict(ac="list", pg=1))
    categories = data.get("class")
    if not isinstance(categories, list) or not any(str(row.get("type_id")) == str(provider.upstream_category) for row in categories if isinstance(row, dict)):
        raise BadRequestError("Japanese animation category not found", reason="catalog_provider_category")
    selected = next(row for row in categories if isinstance(row, dict) and str(row.get("type_id")) == str(provider.upstream_category))
    return dict(ok=True, upstream_category=provider.upstream_category, category_name=plain(selected.get("type_name"), 100), total=integer(data.get("total")),
                categories=[dict(id=integer(row.get("type_id")), name=plain(row.get("type_name"), 100))
                            for row in categories if isinstance(row, dict)])


def integer(value):
    try:
        number = int(str(value))
        if number < 0:
            raise ValueError()
        return number
    except (ValueError, TypeError) as exc:
        raise BadRequestError("Invalid provider number", reason="catalog_provider_payload") from exc


async def preview_import(db, provider_id, payload, actor_id):
    provider = await get_provider(db, provider_id, True)
    items, seen, warnings = [], set(), []
    source_ids = dict((await db.execute(select(CatalogSource.upstream_id, CatalogSource.content_id)
                                        .where(CatalogSource.provider_id == provider_id))).all())
    for page in range(payload.start_page, payload.start_page + payload.page_count):
        data = await provider_client.request_json(provider.id, provider.endpoint, dict(ac="list", t=provider.upstream_category, pg=page))
        if integer(data.get("page")) != page:
            raise BadRequestError("Provider returned a different page", reason="catalog_provider_page")
        if len(data["list"]) > 100:
            raise BadRequestError("Provider page too large", reason="catalog_provider_payload")
        for row in data["list"]:
            if not isinstance(row, dict):
                raise BadRequestError("Invalid provider item", reason="catalog_provider_payload")
            if str(row.get("type_id")) != str(provider.upstream_category):
                warnings.append("category_filtered")
                continue
            upstream_id = integer(row.get("vod_id"))
            if not upstream_id or upstream_id in seen:
                warnings.append("duplicate_filtered")
                continue
            seen.add(upstream_id)
            items.append(dict(upstream_id=upstream_id, title=plain(row.get("vod_name"), 255),
                              status="pending", reason="", content_id=source_ids.get(upstream_id), warnings=[], entries=0))
            if len(items) >= payload.max_items:
                break
        if len(items) >= payload.max_items or not data["list"] or page >= integer(data.get("pagecount")):
            break
    if not items:
        raise BadRequestError("No matching resources", reason="catalog_import_empty")
    job = CatalogImportJob(provider_id=provider_id, provider_version=provider.version, actor_id=actor_id,
                           start_page=payload.start_page, page_count=payload.page_count,
                           items=items, warnings=list(dict.fromkeys(warnings)))
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def start_import(db, job_id, actor_id, retry=False):
    await recover_expired(db)
    job = await get_job(db, job_id)
    if job.query:
        if not retry:
            raise ConflictError("Select preview works first", reason="catalog_import_state")
        from .discovery_service import retry as retry_discovery
        return await retry_discovery(db, job, actor_id)
    provider = await get_provider(db, job.provider_id, True)
    allowed = ("failed", "partial", "interrupted", "cancelled") if retry else ("preview",)
    if job.status not in allowed:
        raise ConflictError("Import state changed", reason="catalog_import_state")
    if provider.version != job.provider_version:
        raise ConflictError("Provider configuration changed; preview again", reason="catalog_import_config")
    created = job.created_at.replace(tzinfo=timezone.utc) if job.created_at.tzinfo is None else job.created_at
    if not retry and (datetime.now(timezone.utc) - created).total_seconds() > 1800:
        raise ConflictError("Preview expired", reason="catalog_import_expired")
    items = [{**row, "status": "pending", "reason": ""} if row["status"] not in SUCCESS else row for row in job.items]
    token = str(uuid.uuid4())
    try:
        result = await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job.id,
            CatalogImportJob.status == job.status).values(status="queued", items=items, actor_id=actor_id,
                lease_token=token, lease_until=time.time() + LEASE_SECONDS, updated_at=func.now()))
        if not result.rowcount:
            raise ConflictError("Import state changed", reason="catalog_import_state")
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Provider already has an active import", reason="catalog_import_busy") from exc
    await db.refresh(job)
    return job, token


async def list_jobs(db, page):
    await recover_expired(db)
    total = await db.scalar(select(func.count()).select_from(CatalogImportJob))
    items = list((await db.scalars(select(CatalogImportJob).order_by(CatalogImportJob.id.desc())
                                  .offset((page - 1) * 10).limit(10))).all())
    return dict(items=items, total=total, page=page, total_pages=ceil(total / 10))


async def cancel_import(db, job_id):
    await get_job(db, job_id)
    result = await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job_id,
        CatalogImportJob.status.in_(["preview", "queued", "running"])).values(
            status="cancelled", lease_token="", updated_at=func.now()))
    if not result.rowcount:
        raise ConflictError("Import state changed", reason="catalog_import_state")
    await db.commit()
    db.expire_all()
    return await get_job(db, job_id)


async def claim(db, job_id, token):
    result = await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job_id,
        CatalogImportJob.lease_token == token, CatalogImportJob.status.in_(["queued", "running"]),
        CatalogImportJob.lease_until >= time.time()).values(status="running",
            lease_until=time.time() + LEASE_SECONDS, updated_at=func.now()))
    return bool(result.rowcount)


async def run_import(job_id, token):
    """A bounded in-process worker with persisted per-item transactions and recovery leases."""
    async with AsyncSessionLocal() as db:
        job = await get_job(db, job_id)
        query = job.query
    if query:
        from .discovery_service import run_discovery, run_aggregate_import
        await (run_discovery(job_id, token) if query["phase"] == "search" else run_aggregate_import(job_id, token))
        return
    try:
        while True:
            async with AsyncSessionLocal() as db:
                if not await claim(db, job_id, token):
                    await db.rollback()
                    return
                job = await get_job(db, job_id)
                index = next((i for i, row in enumerate(job.items) if row["status"] == "pending"), None)
                if index is None:
                    failed = sum(row["status"] == "failed" for row in job.items)
                    job.status = "failed" if failed == len(job.items) else "partial" if failed else "completed"
                    job.lease_token = ""
                    await db.commit()
                    return
                row = job.items[index]
                provider = await get_provider(db, job.provider_id)
                provider_id, endpoint = provider.id, provider.endpoint
                config_valid = provider.enabled and provider.version == job.provider_version
                await db.commit()
            reason, data = "", None
            try:
                if not config_valid:
                    raise BadRequestError("Provider configuration changed", reason="catalog_import_config")
                data = await provider_client.request_json(provider_id, endpoint, dict(ac="detail", ids=row["upstream_id"]))
                if len(data["list"]) != 1 or not isinstance(data["list"][0], dict) or integer(data["list"][0].get("vod_id")) != row["upstream_id"]:
                    raise BadRequestError("Wrong detail ID", reason="catalog_provider_payload")
            except AppError as exc:
                reason = exc.reason
            try:
                async with AsyncSessionLocal() as db:
                    if not await claim(db, job_id, token):
                        await db.rollback()
                        return
                    job = await get_job(db, job_id)
                    provider = await get_provider(db, provider_id)
                    if not provider.enabled or provider.version != job.provider_version:
                        reason = "catalog_import_config"
                    outcome = dict(status="failed", reason=reason, warnings=[])
                    if not reason:
                        detail = data["list"][0]
                        if str(detail.get("type_id")) != str(provider.upstream_category):
                            outcome = dict(status="skipped", reason="category_filtered", warnings=[])
                        else:
                            fields, entries, warnings = parse_detail(detail, provider.category, provider.play_from)
                            outcome = await sync_work(db, provider, row["upstream_id"], fields, entries, job.actor_id)
                            outcome["warnings"] = warnings
                    items = list(job.items)
                    items[index] = {**items[index], **outcome}
                    job.items = items
                    await db.commit()
            except (AppError, ValueError, IntegrityError) as exc:
                # Failed work rolls back together with its mappings/audit; other items continue.
                async with AsyncSessionLocal() as db:
                    if not await claim(db, job_id, token):
                        await db.rollback()
                        return
                    job = await get_job(db, job_id)
                    items = list(job.items)
                    items[index] = {**items[index], "status": "failed", "reason": exc.reason if isinstance(exc, AppError) else "catalog_import_data"}
                    job.items = items
                    await db.commit()
    except (Exception, asyncio.CancelledError):
        logging.getLogger(__name__).exception("Catalog import interrupted: job_id=%s", job_id)
        async with AsyncSessionLocal() as db:
            await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job_id,
                CatalogImportJob.lease_token == token).values(status="interrupted", lease_token="", updated_at=func.now()))
            await db.commit()
