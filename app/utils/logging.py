# app/utils/logging.py
import logging
import json
from datetime import datetime, timezone

_STANDARD_LOG_RECORD_FIELDS = set(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat()
            + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
        }

        # Values supplied through logging's ``extra={...}`` argument are added
        # directly to the LogRecord, rather than under a field named ``extra``.
        # Preserve them so request IDs, paths, durations, and exception types
        # are actually present in structured logs.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and key != "extra":
                log[key] = value

        # Retain compatibility with callers that explicitly attach a nested
        # context dictionary to the record.
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log.update(record.extra)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log["stack"] = self.formatStack(record.stack_info)

        return json.dumps(log, default=str)


logger = logging.getLogger("app")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = []
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # or DEBUG for development
logger.propagate = False


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
