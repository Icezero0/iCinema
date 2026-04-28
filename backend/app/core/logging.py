from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from app.core.config import Settings

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
_configured = False

_LOG_RECORD_RESERVED_KEYS = set(logging.LogRecord(
    name="",
    level=0,
    pathname="",
    lineno=0,
    msg="",
    args=(),
    exc_info=None,
).__dict__)
_LOG_RECORD_RESERVED_KEYS.update({"message", "asctime", "event", "fields"})


class ContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id.get() or "-"
        if not hasattr(record, "user_id"):
            record.user_id = _user_id.get() or "-"
        if not hasattr(record, "event"):
            record.event = "-"
        if not hasattr(record, "fields"):
            record.fields = "-"
        elif isinstance(record.fields, dict):
            record.fields = _format_fields(record.fields)
        return super().format(record)


def configure_logging(settings: Settings, *, force: bool = False) -> None:
    global _configured
    if _configured and not force:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    uvicorn_level = getattr(logging, settings.log_uvicorn_level.upper(), logging.WARNING)

    handler = logging.StreamHandler()
    handler.setFormatter(
        ContextFormatter(
            "%(asctime)s %(levelname)s %(name)s "
            "request_id=%(request_id)s user_id=%(user_id)s event=%(event)s "
            "fields=%(fields)s - %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    app_logger = logging.getLogger("app")
    app_logger.disabled = False
    app_logger.setLevel(level)
    app_logger.propagate = True

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.log_sql else logging.WARNING
    )
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    _configure_uvicorn_loggers(
        uvicorn_level=uvicorn_level,
        enable_access_log=settings.log_uvicorn_access,
    )
    _configured = True
    logging.getLogger("app.startup").info(
        "logging configured level=%s log_sql=%s log_uvicorn_access=%s log_uvicorn_level=%s",
        settings.log_level.upper(),
        settings.log_sql,
        settings.log_uvicorn_access,
        settings.log_uvicorn_level.upper(),
        **log_extra(
            "logging.configured",
            level=settings.log_level.upper(),
            log_sql=settings.log_sql,
            log_uvicorn_access=settings.log_uvicorn_access,
            log_uvicorn_level=settings.log_uvicorn_level.upper(),
        ),
    )


def set_log_context(*, request_id: str | None = None, user_id: int | None = None) -> None:
    if request_id is not None:
        _request_id.set(request_id)
    if user_id is not None:
        _user_id.set(user_id)


def clear_log_context() -> None:
    _request_id.set(None)
    _user_id.set(None)


def log_extra(event: str, **values: Any) -> dict[str, Any]:
    extra: dict[str, Any] = {"event": event}
    fields: dict[str, Any] = {}

    for key, value in values.items():
        if key in {"request_id", "user_id"}:
            extra[key] = value
            continue
        fields[key] = value

    extra["fields"] = fields
    return {"extra": extra}


def _format_fields(fields: dict[str, Any]) -> str:
    if not fields:
        return "-"

    parts = []
    for key in sorted(fields):
        safe_key = f"field_{key}" if key in _LOG_RECORD_RESERVED_KEYS else key
        parts.append(f"{safe_key}={fields[key]}")
    return " ".join(parts)


def _configure_uvicorn_loggers(*, uvicorn_level: int, enable_access_log: bool) -> None:
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.asgi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(uvicorn_level)
        logger.disabled = False

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = True
    access_logger.setLevel(logging.INFO if enable_access_log else logging.WARNING)
    access_logger.disabled = not enable_access_log
