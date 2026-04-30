import logging
import re
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_reasons import ErrorReason
from app.core.logging import log_extra

http_error_logger = logging.getLogger("app.http.error")
security_logger = logging.getLogger("app.security")


def normalize_error_reason(message: str) -> str:
    reason = re.sub(r"[^a-zA-Z0-9]+", "_", message.strip().lower()).strip("_")
    return reason or ErrorReason.APP_ERROR


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "app_error",
        status_code: int = 400,
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.reason = reason or normalize_error_reason(message)
        self.details = details
        super().__init__(message)


class BadRequestError(AppError):
    def __init__(
        self,
        message: str = "Bad request",
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="bad_request",
            status_code=400,
            reason=reason,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="not_found",
            status_code=404,
            reason=reason,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="unauthorized",
            status_code=401,
            reason=reason,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="forbidden",
            status_code=403,
            reason=reason,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="conflict",
            status_code=409,
            reason=reason,
            details=details,
        )


def _http_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
    }.get(status_code, "http_error")


def _validation_error_details(exc: RequestValidationError) -> dict[str, Any]:
    errors = []
    for error in exc.errors():
        item: dict[str, Any] = {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg"),
            "type": error.get("type"),
        }
        if "ctx" in error:
            item["ctx"] = jsonable_encoder(error["ctx"])
        errors.append(item)
    return {"errors": errors}


def _http_status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger = security_logger if exc.status_code in {401, 403} else http_error_logger
        log_method = logger.warning if exc.status_code in {401, 403} else logger.info
        log_method(
            "http app error method=%s path=%s status_code=%s code=%s",
            request.method,
            request.url.path,
            exc.status_code,
            exc.code,
            **log_extra(
                "http.app_error",
                method=request.method,
                path=request.url.path,
                status_code=exc.status_code,
                error_code=exc.code,
                error_message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "reason": exc.reason,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = _validation_error_details(exc)
        http_error_logger.info(
            "http validation error method=%s path=%s status_code=422",
            request.method,
            request.url.path,
            **log_extra(
                "http.validation_error",
                method=request.method,
                path=request.url.path,
                status_code=422,
                error_code="validation_error",
                error_reason=ErrorReason.REQUEST_VALIDATION_FAILED,
            ),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "reason": ErrorReason.REQUEST_VALIDATION_FAILED,
                    "message": "Request validation failed",
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        message = (
            exc.detail
            if isinstance(exc.detail, str)
            else _http_status_phrase(exc.status_code)
        )
        reason = normalize_error_reason(message)
        details = (
            None
            if isinstance(exc.detail, str)
            else {"detail": jsonable_encoder(exc.detail)}
        )
        code = _http_error_code(exc.status_code)
        http_error_logger.info(
            "http exception method=%s path=%s status_code=%s code=%s",
            request.method,
            request.url.path,
            exc.status_code,
            code,
            **log_extra(
                "http.exception",
                method=request.method,
                path=request.url.path,
                status_code=exc.status_code,
                error_code=code,
                error_reason=reason,
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "reason": reason,
                    "message": message,
                    "details": details,
                }
            },
            headers=exc.headers,
        )
