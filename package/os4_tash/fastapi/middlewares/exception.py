"""Exception handlers registered by default in the reusable app factory."""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from ..models import ExceptionHandlerConfig


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    logger.info("HTTP error {}: {}", exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.info("Validation error: {}", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error("Unhandled error: {}", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


handlers = [
    ExceptionHandlerConfig(exception_class=HTTPException, handler=http_exception_handler),
    ExceptionHandlerConfig(
        exception_class=RequestValidationError,
        handler=validation_exception_handler,
    ),
    ExceptionHandlerConfig(exception_class=Exception, handler=unhandled_exception_handler),
]

__all__ = [
    "handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "unhandled_exception_handler",
]
