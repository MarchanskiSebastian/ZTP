from fastapi import FastAPI

from app.REST.web.errors import register_error_handlers
from app.REST.web.routes import router

app = FastAPI(title="Products API")
app.include_router(router)
register_error_handlers(app)
