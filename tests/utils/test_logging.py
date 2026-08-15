import json
import logging

from app.utils.logging import JsonFormatter, get_uvicorn_log_config


def test_json_formatter_includes_extra_context():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=12,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.extra = {"request_id": "req-1"}

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-1"


def test_json_formatter_includes_standard_logging_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app",
        level=logging.ERROR,
        pathname=__file__,
        lineno=12,
        msg="request failed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-2"
    record.path = "/user/create"

    payload = json.loads(formatter.format(record))

    assert payload["request_id"] == "req-2"
    assert payload["path"] == "/user/create"


def test_json_formatter_includes_exception_traceback():
    formatter = JsonFormatter()
    try:
        raise RuntimeError("database schema is stale")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app",
        level=logging.ERROR,
        pathname=__file__,
        lineno=12,
        msg="request failed",
        args=(),
        exc_info=exc_info,
    )

    payload = json.loads(formatter.format(record))

    assert "RuntimeError: database schema is stale" in payload["exception"]


def test_json_formatter_includes_stack_info():
    formatter = JsonFormatter()
    stack_info = "Stack (most recent call last):\n  test frame"
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=12,
        msg="request handled",
        args=(),
        exc_info=None,
        sinfo=stack_info,
    )

    payload = json.loads(formatter.format(record))

    assert payload["stack"] == stack_info


def test_get_uvicorn_log_config_verbose_mode_uses_debug_root_level():
    config = get_uvicorn_log_config(verbose=True)

    assert config["root"]["level"] == "DEBUG"
    assert config["loggers"]["uvicorn"]["level"] == "INFO"
    assert config["loggers"]["app"]["level"] == "DEBUG"


def test_get_uvicorn_log_config_reload_mode_uses_debug_uvicorn_level():
    config = get_uvicorn_log_config(reload=True, verbose=False)

    assert config["root"]["level"] == "INFO"
    assert config["loggers"]["uvicorn"]["level"] == "DEBUG"
    assert config["loggers"]["uvicorn.access"]["propagate"] is False
