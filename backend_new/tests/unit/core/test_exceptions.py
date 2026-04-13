import httpx
from fastapi import FastAPI

from app.core.exceptions import AppError, register_exception_handlers


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
            "message": "broken",
        }
    }
