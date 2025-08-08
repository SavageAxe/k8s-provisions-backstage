from pydantic import ValidationError

from .logger import Logger
from .config import BasicSettings
from loguru import logger


def update_basic_settings(settings: BasicSettings):
    if settings.PROXIED:
        settings.PROXY_LISTEN_PATH = settings.PROXY_LISTEN_PATH.rstrip("/")
        settings.SWAGGER_STATIC_FILES = (
                settings.PROXY_LISTEN_PATH + "/" +
                settings.SWAGGER_STATIC_FILES.lstrip("/")
        )
        settings.SWAGGER_OPENAPI_JSON_URL = (
                settings.PROXY_LISTEN_PATH + "/" +
                settings.OPENAPI_JSON_URL.lstrip("/")
        )
        
        settings.LOG_REQUEST_EXCLUDE_PATHS.extend([
            settings.PROXY_LISTEN_PATH + "/" + path.lstrip("/") 
            for path in settings.LOG_REQUEST_EXCLUDE_PATHS
        ])

    else:
        settings.PROXY_LISTEN_PATH = ""


try:
    basicSettings = BasicSettings()
    update_basic_settings(basicSettings)
except ValidationError as e:
    logger.error(
        f"Configuration error: {e}\n"
        "Please ensure that all required environment variables are set correctly."
    )
    exit(1)

logger_config = Logger(basicSettings.LOG_LEVEL)