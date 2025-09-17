"""Typed representation of exception handlers."""

from typing import Awaitable, Callable, Type, Union

from fastapi import HTTPException, Request
from fastapi.exceptions import ValidationException, WebSocketException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

ExceptionType = Union[
    Type[Exception],
    Type[HTTPException],
    Type[ValidationException],
    Type[WebSocketException],
]

ExceptionInstance = Union[
    Exception,
    HTTPException,
    ValidationException,
    WebSocketException,
]


class ExceptionHandlerConfig(BaseModel):
    exception_class: ExceptionType
    handler: Callable[[Request, ExceptionInstance], Awaitable[JSONResponse]]


__all__ = ["ExceptionHandlerConfig", "ExceptionType", "ExceptionInstance"]
