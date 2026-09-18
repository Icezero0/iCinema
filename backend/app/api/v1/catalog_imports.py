from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.catalog.import_models import CatalogProvider
from app.modules.catalog.import_schemas import ProviderInput, ProviderCreate, ProviderResponse, PreviewInput, ImportResponse, ImportListResponse
from app.modules.catalog import import_service as service
from app.modules.catalog import discovery_service
from app.modules.catalog.import_schemas import DiscoveryInput, SelectionInput
from .catalog import require_catalog_admin

router = APIRouter(prefix="/admin", tags=["catalog-import"], dependencies=[Depends(require_catalog_admin)])


@router.get("/providers", response_model=list[ProviderResponse])
async def providers(db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(CatalogProvider).order_by(CatalogProvider.id))).all())


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: int, payload: ProviderInput, db: AsyncSession = Depends(get_db)):
    return await service.save_provider(db, provider_id, payload)


@router.post("/providers", response_model=ProviderResponse)
async def create_provider(payload: ProviderCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_provider(db, payload)


@router.post("/providers/{provider_id}/check")
async def check_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    return await service.check_provider(db, provider_id)


@router.post("/providers/{provider_id}/preview", response_model=ImportResponse)
async def preview(provider_id: int, payload: PreviewInput, db: AsyncSession = Depends(get_db),
                  user: User = Depends(require_catalog_admin)):
    return await service.preview_import(db, provider_id, payload, user.id)


@router.get("/imports", response_model=ImportListResponse)
async def imports(page: int = Query(default=1, ge=1), db: AsyncSession = Depends(get_db)):
    return await service.list_jobs(db, page)


@router.post("/imports/discover", response_model=ImportResponse)
async def discover(payload: DiscoveryInput, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
                   user: User = Depends(require_catalog_admin)):
    job, token = await discovery_service.discover(db, payload, user.id)
    background.add_task(service.run_import, job.id, token)
    return job


@router.post("/imports/{job_id}/select", response_model=ImportResponse)
async def select_works(job_id: int, payload: SelectionInput, background: BackgroundTasks,
                       db: AsyncSession = Depends(get_db), user: User = Depends(require_catalog_admin)):
    job, token = await discovery_service.select_import(db, job_id, payload.keys, user.id)
    if token:
        background.add_task(service.run_import, job.id, token)
    return job


@router.get("/imports/{job_id}", response_model=ImportResponse)
async def get_import(job_id: int, db: AsyncSession = Depends(get_db)):
    await service.recover_expired(db)
    return await service.get_job(db, job_id)


@router.post("/imports/{job_id}/start", response_model=ImportResponse)
async def start(job_id: int, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
                user: User = Depends(require_catalog_admin)):
    job, token = await service.start_import(db, job_id, user.id)
    background.add_task(service.run_import, job.id, token)
    return job


@router.post("/imports/{job_id}/retry", response_model=ImportResponse)
async def retry(job_id: int, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
                user: User = Depends(require_catalog_admin)):
    job, token = await service.start_import(db, job_id, user.id, retry=True)
    background.add_task(service.run_import, job.id, token)
    return job


@router.post("/imports/{job_id}/cancel", response_model=ImportResponse)
async def cancel(job_id: int, db: AsyncSession = Depends(get_db)):
    return await service.cancel_import(db, job_id)
