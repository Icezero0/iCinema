import httpx
from fastapi import FastAPI, HTTPException

from app.core.exceptions import AppError, register_exception_handlers


# AppError 会被统一异常处理器转换为标准错误响应
async def test_app_error_is_translated_to_standard_error_response() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise AppError("broken", code="broken_code", status_code=418)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/boom")

    assert response.status_code == 418
    assert response.json() == {
        "error": {
            "code": "broken_code",
            "reason": "broken",
            "message": "broken",
            "details": None,
        }
    }


async def test_request_validation_error_uses_standard_error_response() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/items/not-an-int")

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["reason"] == "request_validation_failed"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"]["errors"][0]["loc"] == ["path", "item_id"]
    assert body["error"]["details"]["errors"][0]["type"] == "int_parsing"


async def test_http_exception_uses_standard_error_response() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/conflict")
    async def conflict() -> None:
        raise HTTPException(
            status_code=409,
            detail={"resource": "room", "reason": "duplicate"},
        )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "reason": "conflict",
            "message": "Conflict",
            "details": {"detail": {"resource": "room", "reason": "duplicate"}},
        }
    }
