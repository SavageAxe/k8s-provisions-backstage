"""Middleware that records request processing time."""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils import basicSettings


class TimeRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # pragma: no cover - thin wrapper
        start_time = time.perf_counter_ns()

        response = await call_next(request)

        process_time = time.perf_counter_ns() - start_time
        response.headers[basicSettings.PROCESS_TIME_HEADER] = str(process_time)

        return response


__all__ = ["TimeRequestsMiddleware"]
