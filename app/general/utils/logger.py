from loguru import logger
from colorama import init as colorama_init, Fore, Style
import sys
import logging
import logging.config

colorama_init(autoreset=True)

LOG_COLORS = {
    "TRACE": Fore.BLUE,
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


def formatter(record):
    level = record["level"].name
    color = LOG_COLORS.get(level, "")
    time = record["time"].strftime("%Y-%m-%d %H:%M:%S")
    filename = str(record["file"].name).rstrip(".py")
    func = record["function"]
    line = record["line"]
    message = record["message"]
    return f"{color}{time} - {level} - {filename} - {func}:{line} - {message}{Style.RESET_ALL}\n"


def setup_loguru(logLevel: str = "INFO"):
    logger.remove()
    logger.add(
        sys.stdout,
        level=logLevel,
        format=formatter,
        backtrace=False,
        diagnose=False,
    )


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = LOG_COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


def get_logging_dict(logLevel: str = "INFO"):
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'colored': {
                '()': ColoredFormatter,
                'fmt': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            }
        },
        'handlers': {
            'console': {
                'level': logLevel.upper(),
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
            }
        },
        'loggers': {
            'uvicorn': {
                'level': logLevel.upper(),
                'handlers': ['console'],
                'propagate': False,
            },
            'uvicorn.access': {
                'level': logLevel.upper(),
                'handlers': [],
                'propagate': False,
            },
        }
    }

class Logger:

    def __init__(self, logLevel: str = "INFO"):
        setup_loguru(logLevel)
        self.dict_config = get_logging_dict(logLevel)
        logging.config.dictConfig(self.dict_config)
