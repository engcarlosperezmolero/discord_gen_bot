from typing import Any
from logging.config import dictConfig

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict



LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "with_timestamp": {
            "fmt": "%(asctime)s %(levelprefix)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": False,
        },
    },
    "handlers": {
        "with_timestamp": {
            "formatter": "with_timestamp",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "bot": {"handlers": ["with_timestamp"], "level": "INFO", "propagate": False},
    },
}
dictConfig(LOGGING_CONFIG)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_nested_delimiter="__",
        arbitrary_types_allowed=True,
        extra="ignore",
    )


    BOT_SECRET_TOKEN: str
    PENDING_QUESTION_CHANNEL: str = "pending-questions"


settings = Settings()
