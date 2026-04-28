import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import log_extra

http_error_logger = logging.getLogger("app.http.error")
security_logger = logging.getLogger("app.security")


class AppError(Exception):
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message=message, code="bad_request", status_code=400)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, code="not_found", status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, code="unauthorized", status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, code="forbidden", status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message=message, code="conflict", status_code=409)


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
                    "message": exc.message,
                }
            },
        )
