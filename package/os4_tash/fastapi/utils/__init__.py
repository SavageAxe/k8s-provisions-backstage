"""Utility helpers that back the reusable FastAPI application factory."""

from pydantic import ValidationError
from loguru import logger

from .config import BasicSettings
from .logger import Logger


def update_basic_settings(settings: BasicSettings) -> None:
    """Normalise settings derived from the environment."""

    if settings.PROXIED:
        settings.PROXY_LISTEN_PATH = settings.PROXY_LISTEN_PATH.rstrip("/")
        settings.SWAGGER_STATIC_FILES = (
            settings.PROXY_LISTEN_PATH + "/" + settings.SWAGGER_STATIC_FILES.lstrip("/")
        )
        settings.SWAGGER_OPENAPI_JSON_URL = (
            settings.PROXY_LISTEN_PATH + "/" + settings.OPENAPI_JSON_URL.lstrip("/")
        )
        settings.LOG_REQUEST_EXCLUDE_PATHS.extend(
            [
                settings.PROXY_LISTEN_PATH + "/" + path.lstrip("/")
                for path in settings.LOG_REQUEST_EXCLUDE_PATHS
            ]
        )
    else:
        settings.PROXY_LISTEN_PATH = ""


try:
    basicSettings = BasicSettings()
    update_basic_settings(basicSettings)
except ValidationError as exc:  # pragma: no cover - configuration errors abort startup
    logger.error(
        "Configuration error: {}\n"
        "Please ensure that all required environment variables are set correctly.",
        exc,
    )
    raise SystemExit(1) from exc
else:
    logger_config = Logger(
        log_level=basicSettings.LOG_LEVEL,
        resource=basicSettings.LOG_RESOURCE,
    )

__all__ = [
    "BasicSettings",
    "Logger",
    "basicSettings",
    "logger_config",
    "update_basic_settings",
]
