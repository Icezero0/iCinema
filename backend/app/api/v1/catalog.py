from math import ceil

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.catalog.schemas import (
    AuditListResponse, CategoryResponse, ContentInput, ContentListResponse, ContentResponse,
    ContentStatus, ContentType, ContentUpdate,
)
from app.modules.catalog.service import CatalogService
from app.modules.catalog.models import CatalogEpisode, CatalogLine, CatalogPlayback
from app.modules.catalog.playback_schemas import EpisodeMutation, LineMutation, PlaybackMutation, GraphResponse, PreviewResponse
from app.modules.catalog.playback_service import CatalogPlaybackService
from app.modules.site.constants import SitePermission
from app.modules.site.permissions import require_site_permission
from app.modules.users.models import User


async def require_catalog_admin(user: User = Depends(get_current_user)) -> User:
    require_site_permission(user.site_role, SitePermission.MANAGE_CATALOG)
    return user


router = APIRouter(prefix="/admin/catalog/contents", tags=["catalog-admin"],
                   dependencies=[Depends(require_catalog_admin)])
service = CatalogService()
playback_service = CatalogPlaybackService()
category_router = APIRouter(prefix="/admin/catalog/categories", tags=["catalog-admin"],
                           dependencies=[Depends(require_catalog_admin)])


@category_router.get("", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await service.repo.categories(db)


@router.get("", response_model=ContentListResponse)
async def list_contents(q: str = Query(default="", max_length=255), status: ContentStatus | None = None,
                        category: str | None = Query(default=None, max_length=32),
                        disabled: bool | None = None, content_type: ContentType | None = None,
                        page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
                        db: AsyncSession = Depends(get_db)):
    items, total = await service.repo.list_contents(db, q=q.strip(), status=status, disabled=disabled,
        content_type=content_type, page=page, page_size=page_size, category=category)
    return dict(items=items, total=total, page=page, page_size=page_size, total_pages=ceil(total / page_size))


@router.get("/{content_id}/graph", response_model=GraphResponse)
async def get_graph(content_id: int, db: AsyncSession = Depends(get_db)):
    return await playback_service.graph(db, content_id)


@router.get("/{content_id}/playbacks/{item_id}/preview", response_model=PreviewResponse)
async def preview_playback(content_id: int, item_id: int, db: AsyncSession = Depends(get_db)):
    return await playback_service.preview(db, content_id, item_id)


@router.post("/{content_id}/episodes", response_model=GraphResponse)
async def create_episodes(content_id: int, payload: EpisodeMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogEpisode, content_id, payload, user.id)


@router.put("/{content_id}/episodes/{item_id}", response_model=GraphResponse)
async def update_episodes(content_id: int, item_id: int, payload: EpisodeMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogEpisode, content_id, payload, user.id, item_id)


@router.post("/{content_id}/lines", response_model=GraphResponse)
async def create_lines(content_id: int, payload: LineMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogLine, content_id, payload, user.id)


@router.put("/{content_id}/lines/{item_id}", response_model=GraphResponse)
async def update_lines(content_id: int, item_id: int, payload: LineMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogLine, content_id, payload, user.id, item_id)


@router.post("/{content_id}/playbacks", response_model=GraphResponse)
async def create_playbacks(content_id: int, payload: PlaybackMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogPlayback, content_id, payload, user.id)


@router.put("/{content_id}/playbacks/{item_id}", response_model=GraphResponse)
async def update_playbacks(content_id: int, item_id: int, payload: PlaybackMutation,
        db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    return await playback_service.save(db, CatalogPlayback, content_id, payload, user.id, item_id)



@router.post("", response_model=ContentResponse)
async def create_content(payload: ContentInput, db: AsyncSession = Depends(get_db),
                         user: User = Depends(require_catalog_admin)):
    return await service.create(db, payload, user.id)


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db: AsyncSession = Depends(get_db)):
    return await service.get(db, content_id)


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(content_id: int, payload: ContentUpdate, db: AsyncSession = Depends(get_db),
                         user: User = Depends(require_catalog_admin)):
    return await service.update(db, content_id, payload, user.id)


@router.delete("/{content_id}", status_code=204)
async def delete_content(content_id: int, version: int = Query(ge=1), db: AsyncSession = Depends(get_db)):
    await service.delete(db, content_id, version)
    return Response(status_code=204)


@router.get("/{content_id}/audits", response_model=AuditListResponse)
async def list_audits(content_id: int, page: int = Query(default=1, ge=1),
                      page_size: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    await service.get(db, content_id)
    items, total = await service.repo.audits(db, content_id, page, page_size)
    return dict(items=items, total=total, page=page, page_size=page_size, total_pages=ceil(total / page_size))
