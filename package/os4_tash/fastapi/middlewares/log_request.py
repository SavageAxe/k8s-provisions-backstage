"""Middleware that logs incoming and outgoing HTTP requests."""

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils import basicSettings


class LogRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # pragma: no cover - thin wrapper
        log_level = "INFO"

        if any(
            request.url.path.startswith(prefix)
            for prefix in basicSettings.LOG_REQUEST_EXCLUDE_PATHS
        ):
            log_level = "DEBUG"

        logger.log(log_level, "[Request] {} {}", request.method, request.url.path)

        response = await call_next(request)

        process_time = response.headers.get(basicSettings.PROCESS_TIME_HEADER) or ""

        logger.log(
            log_level,
            "[Response] {} {} {} {}",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )

        return response


__all__ = ["LogRequestsMiddleware"]
