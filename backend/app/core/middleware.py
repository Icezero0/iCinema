from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import clear_log_context, log_extra, set_log_context

access_logger = logging.getLogger("app.http.access")
error_logger = logging.getLogger("app.http.error")
settings = get_settings()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        set_log_context(request_id=request_id)

        started_at = time.perf_counter()
        status_code = 500
        should_log_access = request.url.path not in settings.log_access_exclude_paths

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            error_logger.exception(
                "unhandled http exception method=%s path=%s duration_ms=%s",
                request.method,
                request.url.path,
                duration_ms,
                **log_extra(
                    "http.exception",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                ),
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            user_id = getattr(request.state, "user_id", None)

            if should_log_access:
                access_logger.info(
                    "method=%s path=%s status_code=%s duration_ms=%s client_ip=%s",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    request.client.host if request.client else None,
                    **log_extra(
                        "http.request",
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        client_ip=request.client.host if request.client else None,
                        user_id=user_id if user_id is not None else "-",
                    ),
                )

            response = locals().get("response")
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            clear_log_context()
