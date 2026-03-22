import asyncio
import logging

from app.core.startup import ensure_runtime_paths
from jobs.cleanup_expired_images import run_cleanup_expired_images_once
from jobs.scheduler import run_interval_job


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    await ensure_runtime_paths()

    tasks = [
        asyncio.create_task(
            run_interval_job(
                name="cleanup_expired_images",
                interval_seconds=600,
                job_func=run_cleanup_expired_images_once,
            )
        ),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())