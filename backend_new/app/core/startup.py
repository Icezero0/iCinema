from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()


async def ensure_runtime_paths() -> None:
    settings.data_dir_path.mkdir(parents=True, exist_ok=True)
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)

    settings.avatar_dir_path.mkdir(parents=True, exist_ok=True)
    settings.image_dir_path.mkdir(parents=True, exist_ok=True)
    settings.sticker_dir_path.mkdir(parents=True, exist_ok=True)
    settings.video_dir_path.mkdir(parents=True, exist_ok=True)


async def ensure_database_file() -> None:
    # SQLite 会在首次真实连接时自动创建 db 文件，只要父目录存在。
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))