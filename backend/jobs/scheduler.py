import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_interval_job(
    *,
    name: str,
    interval_seconds: int,
    job_func,
) -> None:
    while True:
        try:
            await job_func()
        except Exception:
            logger.exception("job failed: %s", name)

        await asyncio.sleep(interval_seconds)