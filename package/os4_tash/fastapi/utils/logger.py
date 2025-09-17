"""Logging utilities tailored for FastAPI services."""

from __future__ import annotations

import logging
import logging.config
import sys
from typing import Callable

from loguru import logger


class UvicornHandler(logging.Handler):
    """Bridge standard logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple bridge
        logger.log(
            record.levelname,
            record.getMessage(),
            extra={
                "location": "Uvicorn",
            },
        )


def _base_formatter(resource: str) -> Callable[[dict], str]:
    """Create the base formatter used by Loguru.

    Args:
        resource: Logical resource name that will prefix every log line.
    """

    resource_prefix = f"{resource.upper()}| " if resource else ""

    def formatter(record: dict) -> str:
        extra = record.get("extra", {})
        location = (
            extra.get("location")
            or extra.get("extra", {}).get("location")
            or "{name}:{function}:{line}"
        )
        return (
            f"{resource_prefix}"
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<8}</level> | "
            f"<cyan>{location}</cyan> - "
            "<level>{message}</level>\n"
        )

    return formatter


def setup_loguru(log_level: str = "INFO", resource: str = "") -> None:
    """Configure Loguru with the desired level and formatter."""

    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        format=_base_formatter(resource),
        backtrace=False,
        diagnose=False,
    )


def get_logging_dict(log_level: str = "INFO") -> dict:
    """Generate a :func:`logging.config.dictConfig` mapping for Uvicorn."""

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "UvicornHandler": {
                "level": log_level.upper(),
                "()": UvicornHandler,
            }
        },
        "loggers": {
            "uvicorn": {
                "level": log_level.upper(),
                "handlers": ["UvicornHandler"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": log_level.upper(),
                "handlers": [],
                "propagate": False,
            },
        },
    }


class Logger:
    """Expose a familiar interface that mirrors the application logger."""

    def __init__(self, log_level: str = "INFO", resource: str = "") -> None:
        self.log_level = log_level.upper()
        self.resource = resource.upper()
        setup_loguru(self.log_level, self.resource)
        self.dict_config = get_logging_dict(self.log_level)
        logging.config.dictConfig(self.dict_config)
