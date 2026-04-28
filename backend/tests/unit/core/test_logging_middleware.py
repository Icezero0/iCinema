import logging
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

from app.core.logging import configure_logging, log_extra
from app.core.middleware import RequestLoggingMiddleware


# 验证 HTTP 日志中间件会透传请求 ID，方便前后端和服务端日志对齐。
async def test_request_logging_middleware_returns_request_id_header() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/ping", headers={"X-Request-ID": "req-test"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test"


# 验证默认排除的健康检查路径不会产生 access log 噪音。
async def test_request_logging_middleware_skips_health_access_log(caplog) -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    caplog.set_level(logging.INFO, logger="app.http.access")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert not [
        record
        for record in caplog.records
        if record.name == "app.http.access" and getattr(record, "event", None) == "http.request"
    ]


# 验证鉴权依赖写入的用户 ID 会进入 access log 上下文。
async def test_authenticated_request_access_log_has_user_id(
    api_client,
    factories,
    auth_headers,
    caplog,
) -> None:
    user = await factories.create_user()
    await factories.commit()
    caplog.set_level(logging.INFO, logger="app.http.access")

    response = await api_client.get(
        "/api/v1/users/me",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    access_records = [
        record
        for record in caplog.records
        if record.name == "app.http.access" and getattr(record, "event", None) == "http.request"
    ]
    assert access_records
    assert getattr(access_records[-1], "user_id") == user.id


# 验证业务字段即使与 LogRecord 保留字段同名，也只会进入 fields。
def test_log_extra_keeps_reserved_keys_inside_fields() -> None:
    extra = log_extra("test.event", name="bad-name", msg="bad-msg", user_id=123)["extra"]

    assert extra["event"] == "test.event"
    assert extra["user_id"] == 123
    assert extra["fields"] == {
        "name": "bad-name",
        "msg": "bad-msg",
    }


# 验证默认日志配置会关闭 uvicorn access，并压低 uvicorn lifecycle info。
def test_configure_logging_suppresses_uvicorn_info_by_default() -> None:
    configure_logging(
        SimpleNamespace(
            log_level="INFO",
            log_sql=False,
            log_access_exclude_paths=["/health"],
            log_uvicorn_access=False,
            log_uvicorn_level="WARNING",
        ),
        force=True,
    )

    assert logging.getLogger("uvicorn.access").disabled is True
    assert logging.getLogger("uvicorn.error").level == logging.WARNING
