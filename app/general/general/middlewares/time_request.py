import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils import basicSettings

class TimeRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Middleware to record request time
        """
        start_time = time.perf_counter_ns()

        response = await call_next(request)

        process_time = time.perf_counter_ns() - start_time

        response.headers[basicSettings.PROCESS_TIME_HEADER] = str(process_time)

        return response