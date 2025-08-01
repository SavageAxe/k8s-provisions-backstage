from fastapi import FastAPI

from .log_request import LogRequestsMiddleware
from .time_request import TimeRequestsMiddleware
from .exception import handlers

def add_middlewares(
        app: FastAPI,
        enable_request_logging: bool = True,
        enable_request_timing: bool = True,
        enable_exception_handlers: bool = True
):
    """
    Add middlewares to the FastAPI app.
    """

    if enable_request_timing:
        app.add_middleware(TimeRequestsMiddleware)

    if enable_request_logging:
        app.add_middleware(LogRequestsMiddleware)

    if enable_exception_handlers:
        for handler in handlers:
            app.add_exception_handler(handler.exception_class, handler.handler)