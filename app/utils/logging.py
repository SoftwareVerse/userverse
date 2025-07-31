# app/utils/config/logging.py
import logging
import json
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log.update(record.extra)
        return json.dumps(log)


logger = logging.getLogger("app")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = []
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # or DEBUG for development


def get_uvicorn_log_config(*, reload: bool = False, verbose: bool = False) -> dict:
    level = "DEBUG" if verbose else "INFO"
    uvicorn_level = "INFO" if verbose else ("DEBUG" if reload else "WARNING")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": JsonFormatter}},
        "handlers": {
            "default": {"class": "logging.StreamHandler", "formatter": "json"}
        },
        "root": {"level": level, "handlers": ["default"]},
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": uvicorn_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": uvicorn_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": uvicorn_level,
                "propagate": False,
            },
            "watchfiles": {"level": "WARNING"},
            "app": {"handlers": ["default"], "level": level, "propagate": False},
        },
    }
