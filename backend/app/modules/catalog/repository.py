from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CatalogAudit, CatalogContent, CatalogCategory


class CatalogRepository:
    async def list_contents(self, db: AsyncSession, *, q, status, disabled, content_type, page, page_size, category=None):
        filters = []
        if category is not None:
            filters.append(CatalogContent.category == category)
        if q:
            filters.append(or_(CatalogContent.title.contains(q, autoescape=True),
                               CatalogContent.aliases.contains(q, autoescape=True)))
        if status is not None:
            filters.append(CatalogContent.status == status)
        if disabled is not None:
            filters.append(CatalogContent.disabled == disabled)
        if content_type is not None:
            filters.append(CatalogContent.content_type == content_type)
        total = await db.scalar(select(func.count()).select_from(CatalogContent).where(*filters))
        rows = await db.scalars(select(CatalogContent).where(*filters).order_by(CatalogContent.id.desc())
                                .offset((page - 1) * page_size).limit(page_size))
        return list(rows), total

    async def categories(self, db: AsyncSession):
        return list(await db.scalars(select(CatalogCategory).order_by(CatalogCategory.sort_order, CatalogCategory.code)))

    async def category_exists(self, db: AsyncSession, code: str):
        return await db.get(CatalogCategory, code) is not None

    async def get(self, db: AsyncSession, content_id: int):
        return await db.get(CatalogContent, content_id)

    async def update(self, db: AsyncSession, content_id: int, version: int, values: dict):
        result = await db.execute(update(CatalogContent).where(
            CatalogContent.id == content_id, CatalogContent.version == version,
        ).values(**values, version=version + 1, updated_at=func.now())
            .execution_options(synchronize_session=False))
        return result.rowcount == 1

    async def audits(self, db: AsyncSession, content_id: int, page: int, page_size: int):
        query = select(CatalogAudit).where(CatalogAudit.content_id == content_id)
        total = await db.scalar(select(func.count()).select_from(CatalogAudit).where(CatalogAudit.content_id == content_id))
        items = await db.scalars(query.order_by(CatalogAudit.id.desc()).offset((page - 1) * page_size).limit(page_size))
        return list(items), total
