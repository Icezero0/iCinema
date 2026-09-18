"""Fixed-host, bounded HTTPS metadata requests. Never fetch playback URLs."""
import asyncio
import http.client
import ipaddress
import json
import socket
import ssl
import time

from .parser import invalid

HOST = "omofun.in"
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 12
_request_lock = asyncio.Lock()
_next_request_at = 0.0


def fetch_text(path: str) -> str:
    addresses = socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise invalid("omofun_address")
    conn = http.client.HTTPSConnection(HOST, timeout=TIMEOUT)
    raw = socket.create_connection((addresses[0][4][0], 443), timeout=TIMEOUT)
    try:
        conn.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST)
        conn.request("GET", path, headers={"Accept-Encoding": "identity", "User-Agent": "iCinema/1.0"})
        response = conn.getresponse()
        if response.status == 429 or response.status >= 500:
            raise OSError("Temporary upstream failure")
        if response.status != 200:  # No redirect following.
            raise invalid("omofun_http")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise invalid()
        if int(response.getheader("Content-Length", "0")) > MAX_BYTES:
            raise invalid("omofun_limit")
        chunks, size, deadline = [], 0, time.monotonic() + TIMEOUT
        while size <= MAX_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            if conn.sock:
                conn.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_BYTES:
            raise invalid("omofun_limit")
        return b"".join(chunks).decode("utf-8-sig")
    finally:
        conn.close()
        raw.close()


async def request_text(path: str) -> str:
    global _next_request_at
    for attempt in range(3):
        async with _request_lock:
            await asyncio.sleep(max(0, _next_request_at - time.monotonic()))
            _next_request_at = time.monotonic() + 1.3
        try:
            return await asyncio.to_thread(fetch_text, path)
        except (OSError, http.client.HTTPException):
            if attempt == 2:
                raise invalid("omofun_unavailable")
            await asyncio.sleep(1.3 * 2 ** attempt)
        except (ValueError, UnicodeError):
            raise invalid()


async def request_lines(work_id, episode_id):
    try:
        return json.loads(await request_text(f"/_dyn_plays/{work_id}/{episode_id}"))
    except ValueError as exc:
        raise invalid() from exc
