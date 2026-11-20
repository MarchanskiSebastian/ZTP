from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi


def add_router_docs(app: FastAPI, router: APIRouter, name: str, title: str) -> None:
    """Separate Swagger UI at /docs/<name> showing only the routes of one router."""
    spec_url = f"/docs/{name}/openapi.json"

    @app.get(spec_url, include_in_schema=False)
    def spec():
        return get_openapi(title=title, version="1.0.0", routes=router.routes)

    @app.get(f"/docs/{name}", include_in_schema=False)
    def ui():
        return get_swagger_ui_html(openapi_url=spec_url, title=title)
