from fastapi import Request, HTTPException, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
from app.general.models import ExceptionHandlerConfig
from ..errors.external_service import ExternalServiceError
from typing import Type

async def http_exception_handler(
        request: Request,
        exc: HTTPException
) -> JSONResponse:
    logger.info(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error.",
            "detail": exc.detail
        }
    )


async def external_services_exception_handler(
        request: Request,
        exc: ExternalServiceError
) -> JSONResponse:
    logger.info(f"Request to {exc.service_name} Failed. Error: {exc.error}. Detail: {exc.detail}. Response status code: {exc.status_code}.")
    return JSONResponse(
        status_code=502,
        content={
            "error": exc.error,
            "detail": exc.detail
        }
    )


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
) -> JSONResponse:
    logger.info(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
        "error": "Validation error.",
        "detail": exc.errors()
    }
    )


async def unhandled_exception_handler(
        request: Request,
        exc: Exception
) -> JSONResponse:
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"}
    )

handlers = [
    ExceptionHandlerConfig(
        exception_class=HTTPException,
        handler=http_exception_handler
    ),
    ExceptionHandlerConfig(
        exception_class=RequestValidationError,
        handler=validation_exception_handler
    ),
    ExceptionHandlerConfig(
        exception_class=ExternalServiceError,
        handler=external_services_exception_handler
    ),
    ExceptionHandlerConfig(
        exception_class=Exception,
        handler=unhandled_exception_handler
    )
]

def add_exception_handlers(app: FastAPI) -> None:
    for handler_config in handlers:
        app.add_exception_handler(handler_config.exception_class, handler_config.handler)