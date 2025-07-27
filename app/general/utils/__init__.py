from pydantic import ValidationError

from app.general.utils.logger import Logger
from app.general.utils.config import BasicSettings

try:
    basicSettings = BasicSettings()
except ValidationError as e:
    print(
        f"Configuration error: {e}\n"
        "Please ensure that all required environment variables are set correctly."
    )
    exit(1)

logger_config = Logger(basicSettings.LOG_LEVEL)