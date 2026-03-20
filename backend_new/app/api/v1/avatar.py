from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(tags=["avatar"])
settings = get_settings()


@router.get("/avatar/{key}")
async def get_avatar(key: str):
    if "/" in key or "\\" in key or ".." in key:
        raise HTTPException(status_code=400, detail="Invalid avatar key")

    file_path = settings.avatar_dir_path / key
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(str(file_path))