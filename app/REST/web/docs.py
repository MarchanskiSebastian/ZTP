from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi


def add_tag_docs(app: FastAPI, tag: str, title: str) -> None:
    """Separate Swagger UI at /docs/<tag> showing only the routes of one tag."""
    spec_url = f"/docs/{tag}/openapi.json"

    @app.get(spec_url, include_in_schema=False)
    def spec():
        routes = [r for r in app.routes if tag in getattr(r, "tags", [])]
        return get_openapi(title=title, version="1.0.0", routes=routes)

    @app.get(f"/docs/{tag}", include_in_schema=False)
    def ui():
        return get_swagger_ui_html(openapi_url=spec_url, title=title)
