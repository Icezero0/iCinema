from fastapi import APIRouter, BackgroundTasks, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.omofun.service import read_cache, resolve, run_parse
from app.modules.omofun.room_service import read_room, resolve_room
from app.modules.users.models import User

router = APIRouter(prefix="/omofun", tags=["omofun"], dependencies=[Depends(get_current_user)])


class ResolveInput(BaseModel):
    value: str = Field(min_length=1, max_length=2048)
    force: bool = False


@router.get("/rooms/{room_id}")
async def get_room_resolution(room_id: int, response: Response, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return await read_room(db, room_id, user.id)


@router.post("/rooms/{room_id}/resolve")
async def resolve_room_work(room_id: int, payload: ResolveInput, tasks: BackgroundTasks, response: Response,
                           db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result, token, work_id = await resolve_room(db, room_id, user.id, payload.value, payload.force)
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    if token:
        tasks.add_task(run_parse, work_id, token)
    return result


@router.post("/resolve")
async def resolve_work(payload: ResolveInput, tasks: BackgroundTasks, response: Response,
                       db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result, token = await resolve(db, payload.value, payload.force, user.id)
    await db.commit()  # Do not retain a read transaction during the background parse.
    response.headers["Cache-Control"] = "no-store"
    if token:
        tasks.add_task(run_parse, result["work_id"], token)
    return result


@router.get("/{work_id}")
async def get_work(work_id: str, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return await read_cache(db, work_id)
