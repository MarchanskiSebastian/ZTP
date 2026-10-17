from fastapi import FastAPI

from web.routes import router

app = FastAPI(title="Products API")
app.include_router(router)
