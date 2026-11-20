from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.REST.service.product_validators import (
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)

# Domain exception -> HTTP status code
# IntegrityError: e.g. two concurrent POSTs with the same idempotency_key
_STATUS = {ValidationError: 422, ConflictError: 409, ResourceNotFoundError: 400, IntegrityError: 409}


def register_error_handlers(app: FastAPI) -> None:
    for exc_type, status_code in _STATUS.items():

        async def handler(request: Request, exc: Exception, code: int = status_code):
            return JSONResponse(status_code=code, content={"detail": str(exc)})

        app.add_exception_handler(exc_type, handler)
