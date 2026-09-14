"""Bound actual request bytes before FastAPI's multipart parser allocates files."""
from tempfile import SpooledTemporaryFile

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def reject():
            response = JSONResponse(status_code=413, content={"error": {
                "code": "payload_too_large", "reason": "request_body_too_large",
                "message": "Request body is too large", "details": {"max_bytes": self.max_bytes},
            }})
            await response(scope, receive, send)

        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        return await reject()
                except ValueError:
                    pass  # The actual byte count remains authoritative.

        with SpooledTemporaryFile(max_size=1024 * 1024) as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > self.max_bytes:
                    return await reject()
                await run_in_threadpool(body.write, chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            remaining = size
            delivered = False

            async def bounded_receive():
                nonlocal remaining, delivered
                if delivered:
                    return await receive()
                chunk = await run_in_threadpool(body.read, 64 * 1024)
                remaining -= len(chunk)
                delivered = remaining == 0
                return {"type": "http.request", "body": chunk, "more_body": not delivered}

            await self.app(scope, bounded_receive, send)
