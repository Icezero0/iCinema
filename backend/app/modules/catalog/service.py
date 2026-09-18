from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from copy import deepcopy

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from .models import CatalogAudit, CatalogContent, CatalogPlayback, CatalogEpisode, CatalogLine
from .import_models import CatalogSource, CatalogImportJob
from .repository import CatalogRepository
from .schemas import ContentInput, ContentUpdate


class CatalogService:
    def __init__(self):
        self.repo = CatalogRepository()

    async def get(self, db: AsyncSession, content_id: int):
        item = await self.repo.get(db, content_id)
        if item is None:
            raise NotFoundError("资源不存在", reason="catalog_content_not_found")
        return item

    async def create(self, db: AsyncSession, payload: ContentInput, actor_id: int):
        await self.require_category(db, payload.category)
        values = payload.model_dump()
        item = CatalogContent(**values)
        db.add(item)
        await db.flush()
        db.add(CatalogAudit(content_id=item.id, actor_id=actor_id, action="create",
                            changes={key: {"before": None, "after": value} for key, value in values.items()}))
        await db.commit()
        await db.refresh(item)
        return item

    async def update(self, db: AsyncSession, content_id: int, payload: ContentUpdate, actor_id: int):
        item = await self.get(db, content_id)
        await self.require_category(db, payload.category)
        if item.version != payload.version:
            raise ConflictError("资源已被其他操作修改，请重新打开后编辑", reason="catalog_version_conflict")
        values = payload.model_dump(exclude={"version"})
        changes = {key: {"before": getattr(item, key), "after": value}
                   for key, value in values.items() if getattr(item, key) != value}
        if not changes:
            return item
        if not await self.repo.update(db, content_id, payload.version, values):
            await db.rollback()
            raise ConflictError("资源已被其他操作修改，请重新打开后编辑", reason="catalog_version_conflict")
        db.add(CatalogAudit(content_id=content_id, actor_id=actor_id, action="update", changes=changes))
        await db.commit()
        await db.refresh(item)
        return item

    async def require_category(self, db: AsyncSession, code: str):
        if not await self.repo.category_exists(db, code):
            raise BadRequestError("Unknown catalog category", reason="catalog_category_not_found")

    async def delete(self, db: AsyncSession, content_id: int, version: int):
        await self.get(db, content_id)
        if not await self.repo.update(db, content_id, version, {}):
            await db.rollback()
            raise ConflictError("Resource changed", reason="catalog_version_conflict")
        sources = set((await db.execute(select(CatalogSource.provider_id, CatalogSource.upstream_id)
                                        .where(CatalogSource.content_id == content_id))).all())
        # Invalidate old workers/previews so deleting a work cannot immediately recreate it.
        for job in (await db.scalars(select(CatalogImportJob))).all():
            items, touched = deepcopy(job.items), False
            for item in items:
                identities = {(s['provider_id'], s['upstream_id']) for s in item.get('sources', [])}
                if not item.get('sources'):
                    identities.add((job.provider_id, item['upstream_id']))
                if item.get('content_id') == content_id or identities & sources:
                    item.update(content_id=None, status='skipped', reason='catalog_content_deleted', blocked=True,
                                match='deleted')
                    touched = True
            if touched:
                job.items = items
                if job.status in ('preview', 'queued', 'running'):
                    job.status, job.lease_token = 'cancelled', ''
        for model in (CatalogSource, CatalogPlayback, CatalogEpisode, CatalogLine, CatalogAudit):
            await db.execute(delete(model).where(model.content_id == content_id))
        await db.execute(delete(CatalogContent).where(CatalogContent.id == content_id))
        await db.commit()
