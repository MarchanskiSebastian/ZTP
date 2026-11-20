import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bff.routes import router as bff_router
from app.cart.routes import cart_router, orders_router
from app.identity.routes import router as identity_router
from app.REST.service.worker import run_forever
from app.REST.web.docs import add_router_docs
from app.REST.web.errors import register_error_handlers
from app.REST.web.metrics import router as metrics_router
from app.REST.web.notification_routes import router as notification_router
from app.REST.web.routes import router as products_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(run_forever()) if os.getenv("WORKER_ENABLED", "1") == "1" else None
    yield
    if worker:
        worker.cancel()


app = FastAPI(title="ZTP API", lifespan=lifespan)
for r in (products_router, notification_router, metrics_router, identity_router, cart_router, orders_router,
          bff_router):
    app.include_router(r)
register_error_handlers(app)
add_router_docs(app, [products_router], "/docs/products", "Products API")
add_router_docs(app, [notification_router], "/docs/notifications", "Notifications API")
add_router_docs(app, [identity_router], "/identity-docs", "Identity API")
add_router_docs(app, [cart_router, orders_router, bff_router], "/cart-docs", "Cart & Orders API")
