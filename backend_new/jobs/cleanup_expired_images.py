import logging

from app.core.database import AsyncSessionLocal
from app.modules.media.service import MediaService

logger = logging.getLogger(__name__)


async def run_cleanup_expired_images_once(batch_size: int = 100) -> int:
    media_service = MediaService()
    total = 0

    async with AsyncSessionLocal() as db:
        while True:
            count = await media_service.cleanup_expired_images(
                db,
                batch_size=batch_size,
            )
            total += count
            if count < batch_size:
                break

    logger.info("cleanup_expired_images total=%s", total)
    return total