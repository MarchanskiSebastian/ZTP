from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi


def add_router_docs(app: FastAPI, routers: list[APIRouter], path: str, title: str) -> None:
    """Separate Swagger UI at `path` showing only the routes of the given routers."""
    spec_url = f"{path}/openapi.json"

    @app.get(spec_url, include_in_schema=False)
    def spec():
        routes = [r for router in routers for r in router.routes]
        return get_openapi(title=title, version="1.0.0", routes=routes)

    @app.get(path, include_in_schema=False)
    def ui():
        return get_swagger_ui_html(openapi_url=spec_url, title=title)
