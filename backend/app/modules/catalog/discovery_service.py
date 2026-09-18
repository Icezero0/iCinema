"""Persisted, cancellable all-provider discovery and conservative work aggregation."""
import logging
import time
import unicodedata
import uuid
from copy import deepcopy
from datetime import datetime, timezone, date

from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppError, BadRequestError, ConflictError
from . import import_service as service, provider_client
from .import_models import CatalogProvider, CatalogImportJob, CatalogSource
from .models import CatalogContent, CatalogEpisode
from .import_parser import parse_detail, plain
from .import_sync import sync_work


def normalized(value):
    # Keep season numbers, punctuation and subtitle words; never strip sequel markers.
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def matches(left, right):
    return (normalized(left["title"]) == normalized(right["title"])
            and left["category"] == right["category"]
            and all(not left.get(key) or not right.get(key) or left[key] == right[key]
                    for key in ("year", "region", "content_type")))


async def discover(db, payload, actor_id):
    await service.recover_expired(db)
    await service.CatalogService().require_category(db, payload.category)
    providers = list((await db.scalars(select(CatalogProvider).where(
        CatalogProvider.enabled.is_(True), CatalogProvider.category == payload.category
    ).order_by(CatalogProvider.id))).all())
    if not providers:
        raise BadRequestError("No enabled providers for category", reason="catalog_discovery_no_provider")
    token = str(uuid.uuid4())
    query = dict(criteria=payload.model_dump(mode="json"), phase="search", complete=False,
                 providers=[dict(id=p.id, version=p.version, name=p.name) for p in providers],
                 provider_index=0, page=1, scanned=0, total_pages=0, failures=[], ready_at=None)
    job = CatalogImportJob(provider_id=providers[0].id, provider_version=providers[0].version,
        actor_id=actor_id, start_page=1, page_count=0, status="queued", query=query,
        items=[], warnings=[], lease_token=token, lease_until=time.time() + service.LEASE_SECONDS)
    db.add(job)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Discovery already running", reason="catalog_import_busy") from exc
    await db.refresh(job)
    return job, token


async def checked_provider(db, snapshot):
    provider = await service.get_provider(db, snapshot["id"], True)
    if provider.version != snapshot["version"]:
        raise ConflictError("Provider changed", reason="catalog_import_config")
    return provider


def in_range(row, criteria):
    if normalized(criteria["name"]) not in normalized(plain(row.get("vod_name"), 255)):
        return False
    start, end = criteria.get("updated_from"), criteria.get("updated_to")
    if start or end:
        try:
            updated = date.fromisoformat(str(row.get("vod_time", ""))[:10]).isoformat()
        except ValueError:
            raise BadRequestError("Missing upstream update date", reason="catalog_discovery_date")
        return (not start or updated >= start) and (not end or updated <= end)
    return True


async def add_candidate(db, job, provider, detail, updated):
    fields, entries, warnings = parse_detail(detail, provider.category, provider.play_from)
    uid = service.integer(detail.get("vod_id"))
    source = await db.scalar(select(CatalogSource).where(
        CatalogSource.provider_id == provider.id, CatalogSource.upstream_id == uid))
    if source:
        targets = [await db.get(CatalogContent, source.content_id)]
    else:
        local = (await db.scalars(select(CatalogContent).where(CatalogContent.category == provider.category))).all()
        targets = [item for item in local if matches(fields, {key: getattr(item, key) for key in
                   ("title", "category", "year", "region", "content_type")})]
    target = targets[0] if len(targets) == 1 else None
    items = deepcopy(job.items)
    identity = f"{provider.id}:{uid}"
    if any(any(s["provider_id"] == provider.id and s["upstream_id"] == uid for s in i["sources"]) for i in items):
        return
    compatible = [i for i in items if (target and i["content_id"] == target.id) or
                  ((not target or not i["content_id"]) and all(matches(fields, s["fields"]) for s in i["sources"]))]
    # Two records from one site must not overwrite the same provider line.
    group = compatible[0] if len(compatible) == 1 and len(targets) <= 1 else None
    if group and any(s["provider_id"] == provider.id for s in group["sources"]):
        group["blocked"] = True
        group["match"] = "ambiguous"
        group = None
        ambiguous = True
    else:
        ambiguous = len(targets) > 1 or len(compatible) > 1
    if group is None:
        group = dict(key=identity, upstream_id=uid, title=target.title if target else fields["title"],
            status="pending", reason="", warnings=[], entries=0, sources=[],
            content_id=target.id if target else None, target_version=target.version if target else None,
            blocked=ambiguous or bool(target and target.disabled),
            match="ambiguous" if ambiguous else "disabled" if target and target.disabled else "linked" if source else "metadata")
        items.append(group)
    elif target and not group["content_id"]:
        group.update(content_id=target.id, target_version=target.version, title=target.title,
                     blocked=group["blocked"] or target.disabled,
                     match="disabled" if target.disabled else "linked" if source else "metadata")
    group.update(status="pending", reason="")
    group["sources"] = [*group["sources"], dict(provider_id=provider.id, provider_name=provider.name,
        upstream_id=uid, title=fields["title"], updated=updated, episode_count=len(entries), warnings=warnings,
        fields=fields, entries=entries)]
    identities = {(e["kind"], e["number"]) for s in group["sources"] for e in s["entries"]}
    existing = set((await db.execute(select(CatalogEpisode.kind, CatalogEpisode.number).where(
        CatalogEpisode.content_id == group["content_id"]))).all()) if group["content_id"] else set()
    group.update(line_count=sum(bool(s["entries"]) for s in group["sources"]),
        episode_count=len(identities), new_episodes=len(identities - existing),
        entries=sum(len(s["entries"]) for s in group["sources"]))
    if not group["line_count"]:
        group["blocked"] = True
        group["match"] = "no_hls"
    elif group["match"] == "no_hls":
        group["blocked"] = False
        group["match"] = "metadata"
    job.items = items


async def run_discovery(job_id, token):
    try:
        while True:
            async with AsyncSessionLocal() as db:
                if not await service.claim(db, job_id, token):
                    return
                job = await service.get_job(db, job_id)
                q = dict(job.query)
                if q["provider_index"] >= len(q["providers"]):
                    q.update(complete=not q["failures"], ready_at=datetime.now(timezone.utc).isoformat())
                    job.query, job.status, job.lease_token = q, "failed" if q["failures"] else "preview", ""
                    await db.commit()
                    return
                snapshot = q["providers"][q["provider_index"]]
                provider = await service.get_provider(db, snapshot["id"])
                endpoint, category, page = provider.endpoint, provider.upstream_category, q["page"]
                await db.commit()
            try:
                async with AsyncSessionLocal() as db:
                    await checked_provider(db, snapshot)
                data = await provider_client.request_json(snapshot["id"], endpoint, dict(ac="list", t=category, pg=page))
                if service.integer(data.get("page")) != page or len(data["list"]) > 100:
                    raise BadRequestError("Invalid page", reason="catalog_provider_page")
                total_pages = service.integer(data.get("pagecount"))
                if total_pages > 1000:
                    raise BadRequestError("Directory limit reached", reason="catalog_discovery_limit")
                for row in data["list"]:
                    if not isinstance(row, dict):
                        raise BadRequestError("Invalid row", reason="catalog_provider_payload")
                    if str(row.get("type_id")) != str(category) or not in_range(row, q["criteria"]):
                        continue
                    uid = service.integer(row.get("vod_id"))
                    async with AsyncSessionLocal() as db:
                        if not await service.claim(db, job_id, token):
                            return
                        await db.commit()
                    detail = await provider_client.request_json(snapshot["id"], endpoint, dict(ac="detail", ids=uid))
                    if (len(detail["list"]) != 1 or not isinstance(detail["list"][0], dict)
                            or service.integer(detail["list"][0].get("vod_id")) != uid):
                        raise BadRequestError("Wrong detail", reason="catalog_provider_payload")
                    async with AsyncSessionLocal() as db:
                        if not await service.claim(db, job_id, token):
                            return
                        job = await service.get_job(db, job_id)
                        provider = await checked_provider(db, snapshot)
                        if str(detail["list"][0].get("type_id")) != str(provider.upstream_category):
                            raise BadRequestError("Category changed", reason="catalog_provider_category")
                        if len(job.items) >= 5000:
                            raise BadRequestError("Candidate limit reached", reason="catalog_discovery_limit")
                        await add_candidate(db, job, provider, detail["list"][0], plain(row.get("vod_time"), 40))
                        await db.commit()
                async with AsyncSessionLocal() as db:
                    if not await service.claim(db, job_id, token):
                        return
                    job = await service.get_job(db, job_id)
                    q = dict(job.query)
                    q.update(scanned=q["scanned"] + len(data["list"]), total_pages=total_pages, page=page + 1)
                    if page >= total_pages or not data["list"]:
                        q.update(provider_index=q["provider_index"] + 1, page=1)
                    job.query = q
                    await db.commit()
            except (AppError, ValueError, TypeError) as exc:
                async with AsyncSessionLocal() as db:
                    if not await service.claim(db, job_id, token):
                        return
                    job = await service.get_job(db, job_id)
                    q = dict(job.query)
                    q["failures"] = [*q["failures"], dict(name=snapshot["name"], reason=exc.reason if isinstance(exc, AppError) else "catalog_import_data")]
                    q.update(provider_index=q["provider_index"] + 1, page=1)
                    job.query = q
                    await db.commit()
    except Exception:
        logging.getLogger(__name__).exception("Discovery interrupted: %s", job_id)
        async with AsyncSessionLocal() as db:
            await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job_id,
                CatalogImportJob.lease_token == token).values(status="interrupted", lease_token=""))
            await db.commit()


async def select_import(db, job_id, keys, actor_id):
    await service.recover_expired(db)
    job = await service.get_job(db, job_id)
    if job.query.get("phase") == "search" and job.status in ("queued", "running", "cancelled"):
        # Claim a write lock before re-reading the JSON snapshot. Discovery uses
        # the same row lock through claim(), so neither writer loses new results.
        locked = await db.execute(update(CatalogImportJob).where(
            CatalogImportJob.id == job_id, CatalogImportJob.status == job.status,
            CatalogImportJob.lease_token == job.lease_token,
        ).values(status=CatalogImportJob.status))
        if not locked.rowcount:
            raise ConflictError("State changed", reason="catalog_import_state")
        await db.refresh(job)
        items = deepcopy(job.items)
        chosen = [item for item in items if item["key"] in keys]
        if not chosen or len(chosen) != len(set(keys)) or any(item["blocked"] for item in chosen):
            raise BadRequestError("Invalid selection", reason="catalog_discovery_selection")
        # Local database writes only: no provider requests while holding the lock.
        previous_actor = job.actor_id
        job.actor_id = actor_id
        for item in chosen:
            outcome = await import_group(db, job, item)
            item.update(outcome)
            target = await db.get(CatalogContent, outcome["content_id"])
            await db.refresh(target)
            item.update(target_version=target.version, new_episodes=0)
        job.actor_id = previous_actor
        job.items = items
        await db.commit()
        await db.refresh(job)
        return job, None
    if job.status != "preview" or not job.query:
        raise ConflictError("Not a discovery preview", reason="catalog_import_state")
    ready = datetime.fromisoformat(job.query["ready_at"])
    if (datetime.now(timezone.utc) - ready).total_seconds() > 1800:
        raise ConflictError("Preview expired", reason="catalog_import_expired")
    items = [i for i in job.items if i["key"] in keys]
    if len(items) != len(set(keys)) or any(i["blocked"] for i in items):
        raise BadRequestError("Invalid selection", reason="catalog_discovery_selection")
    for snapshot in job.query["providers"]:
        await checked_provider(db, snapshot)
    token = str(uuid.uuid4())
    q = {**job.query, "phase": "import"}
    try:
        result = await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job.id,
            CatalogImportJob.status == "preview").values(items=items, query=q, actor_id=actor_id,
            status="queued", lease_token=token, lease_until=time.time() + service.LEASE_SECONDS))
        if not result.rowcount:
            raise ConflictError("State changed", reason="catalog_import_state")
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Import busy", reason="catalog_import_busy") from exc
    await db.refresh(job)
    return job, token


async def import_group(db, job, row):
    target_id = row["content_id"]
    if target_id:
        target = await db.get(CatalogContent, target_id)
        if not target or target.version != row["target_version"]:
            raise ConflictError("Work changed since preview", reason="catalog_version_conflict")
    else:
        # Detect catalog/source changes since the preview instead of creating duplicates.
        for source in row["sources"]:
            linked = await db.scalar(select(CatalogSource).where(CatalogSource.provider_id == source["provider_id"],
                                                               CatalogSource.upstream_id == source["upstream_id"]))
            local = (await db.scalars(select(CatalogContent).where(CatalogContent.category == source["fields"]["category"]))).all()
            if linked or any(matches(source["fields"], {k: getattr(c, k) for k in ("title", "category", "year", "region", "content_type")}) for c in local):
                raise ConflictError("Catalog changed; search again", reason="catalog_version_conflict")
    results = []
    for source in row["sources"]:
        if not source["entries"]:
            continue
        snapshot = next(p for p in job.query["providers"] if p["id"] == source["provider_id"])
        provider = await checked_provider(db, snapshot)
        result = await sync_work(db, provider, source["upstream_id"], source["fields"], source["entries"], job.actor_id, target_id)
        target_id = result["content_id"]
        results.append(result)
        await db.flush()
        # Refresh ORM versions changed by CAS SQL before adding the next source.
        await db.refresh(await db.get(CatalogContent, target_id))
    status = next((s for s in ("created", "updated", "skipped") if any(r["status"] == s for r in results)), "unchanged")
    return dict(status=status, reason="work_disabled" if status == "skipped" else "", content_id=target_id)


async def run_aggregate_import(job_id, token):
    while True:
        index = None
        try:
            async with AsyncSessionLocal() as db:
                if not await service.claim(db, job_id, token):
                    return
                job = await service.get_job(db, job_id)
                index = next((i for i, row in enumerate(job.items) if row["status"] == "pending"), None)
                if index is None:
                    failed = sum(i["status"] == "failed" for i in job.items)
                    job.status = "failed" if failed == len(job.items) else "partial" if failed else "completed"
                    job.lease_token = ""
                    await db.commit()
                    return
                items = list(job.items)
                outcome = await import_group(db, job, items[index])
                job = await service.get_job(db, job_id)
                items[index] = {**items[index], **outcome}
                job.items = items
                await db.commit()
        except Exception as exc:
            logging.getLogger(__name__).exception("Aggregate import item failed: %s", job_id)
            async with AsyncSessionLocal() as db:
                if not await service.claim(db, job_id, token):
                    return
                job = await service.get_job(db, job_id)
                if index is None:
                    job.status, job.lease_token = "interrupted", ""
                else:
                    items = list(job.items)
                    items[index] = {**items[index], "status": "failed", "reason": exc.reason if isinstance(exc, AppError) else "catalog_import_data"}
                    job.items = items
                await db.commit()
            if index is None:
                return


async def retry(db, job, actor_id):
    if job.status not in ("failed", "partial", "interrupted", "cancelled"):
        raise ConflictError("State changed", reason="catalog_import_state")
    for snapshot in job.query["providers"]:
        await checked_provider(db, snapshot)
    q = dict(job.query)
    if q["phase"] == "search":
        q.update(provider_index=0, page=1, scanned=0, failures=[], complete=False, ready_at=None)
        items = []
    else:
        if (datetime.now(timezone.utc) - datetime.fromisoformat(q["ready_at"])).total_seconds() > 1800:
            raise ConflictError("Preview expired", reason="catalog_import_expired")
        items = [{**i, "status": "pending", "reason": ""} if i["status"] not in service.SUCCESS else i for i in job.items]
    token = str(uuid.uuid4())
    try:
        result = await db.execute(update(CatalogImportJob).where(CatalogImportJob.id == job.id,
            CatalogImportJob.status == job.status).values(status="queued", query=q, items=items,
            actor_id=actor_id, lease_token=token, lease_until=time.time() + service.LEASE_SECONDS))
        if not result.rowcount:
            raise ConflictError("State changed", reason="catalog_import_state")
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Import busy", reason="catalog_import_busy") from exc
    await db.refresh(job)
    return job, token
