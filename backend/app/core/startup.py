from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.core.logging import log_extra

settings = get_settings()
logger = logging.getLogger("app.startup")


async def ensure_runtime_paths() -> None:
    settings.data_dir_path.mkdir(parents=True, exist_ok=True)
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)

    settings.avatar_dir_path.mkdir(parents=True, exist_ok=True)
    settings.image_dir_path.mkdir(parents=True, exist_ok=True)
    settings.sticker_dir_path.mkdir(parents=True, exist_ok=True)
    settings.video_dir_path.mkdir(parents=True, exist_ok=True)
    settings.feedback_image_dir_path.mkdir(parents=True, exist_ok=True)


def _build_alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini_path = project_root / "alembic.ini"
    alembic_dir_path = project_root / "alembic"

    config = Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(alembic_dir_path))
    config.set_main_option("sqlalchemy.url", settings.alembic_database_url)
    return config


def _upgrade_database_to_head() -> None:
    command.upgrade(_build_alembic_config(), "head")


async def ensure_database_schema() -> None:
    logger.info(
        "running database migrations to head",
        **log_extra("startup.migrations_start"),
    )
    await asyncio.to_thread(_upgrade_database_to_head)
    logger.info(
        "database migrations complete",
        **log_extra("startup.migrations_complete"),
    )


async def initialize_runtime() -> None:
    await ensure_runtime_paths()
    await ensure_database_schema()
