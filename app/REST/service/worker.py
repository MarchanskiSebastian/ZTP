import asyncio
import logging
import os

from app.REST.data.database import SessionLocal
from app.REST.service.notification_service import process_ready

WORKER_INTERVAL = float(os.getenv("WORKER_INTERVAL_SECONDS", "5"))
log = logging.getLogger("notifications.worker")


def run_once() -> dict[str, int]:
    db = SessionLocal()
    try:
        return process_ready(db)
    finally:
        db.close()


async def run_forever() -> None:
    """Background loop started with the app (see main.py lifespan)."""
    while True:
        try:
            # blocking DB/SMTP/HTTP work runs in a thread so the event loop keeps serving requests
            result = await asyncio.to_thread(run_once)
            if result["processed"]:
                log.info("worker: %s", result)
        except Exception:
            log.exception("worker iteration failed")  # e.g. DB down: try again next tick
        await asyncio.sleep(WORKER_INTERVAL)
