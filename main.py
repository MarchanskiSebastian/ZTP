import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.REST.web.docs import add_router_docs
from app.REST.web.errors import register_error_handlers
from app.REST.web.metrics import router as metrics_router
from app.REST.web.notification_routes import router as notification_router
from app.REST.web.routes import router
from app.REST.service.worker import run_forever


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(run_forever()) if os.getenv("WORKER_ENABLED", "1") == "1" else None
    yield
    if worker:
        worker.cancel()


app = FastAPI(title="ZTP API", lifespan=lifespan)
app.include_router(router)
app.include_router(notification_router)
app.include_router(metrics_router)
register_error_handlers(app)
add_router_docs(app, router, "products", "Products API")
add_router_docs(app, notification_router, "notifications", "Notifications API")
