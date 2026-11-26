import asyncio
import logging
import uvicorn
from app.config import settings
from app.database.models import init_db
from app.main import app
from app.worker import WebWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket_fox_web.runner")


async def main():
    logger.info(f"Starting {settings.APP_NAME} Unified Runner (API + Worker)...")
    await init_db()
    logger.info(
        "API on http://%s:%d | worker=%s | poll every %ds",
        settings.HOST,
        settings.PORT,
        settings.WORKER_ENABLED,
        settings.POLL_INTERVAL_SECONDS,
    )

    config = uvicorn.Config(
        app=app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve())]
    if settings.WORKER_ENABLED:
        tasks.append(asyncio.create_task(WebWorker().start()))
    else:
        logger.warning("WORKER_ENABLED=false — no watches will be polled in this process.")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        # Shut the worker down with the API so Ctrl+C exits cleanly instead of
        # leaving a pending polling task behind.
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Ticket Fox Web stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

