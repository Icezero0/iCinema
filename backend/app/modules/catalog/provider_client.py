"""Bounded public HTTPS JSON transport; no redirects or third-party player code."""
import asyncio
import http.client
import ipaddress
import json
import socket
import ssl
import time
from urllib.parse import urlencode, urlsplit

from sqlalchemy import update

from app.core.exceptions import BadRequestError
from .import_models import CatalogProvider

ENDPOINT = "https://jyzyapi.com/provide/vod/from/jinyingm3u8/at/json"
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 12


def validate_endpoint(endpoint: str):
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname or ""
        if (parsed.scheme != "https" or not host or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
                or "\\" in endpoint or any(ord(char) < 33 or ord(char) == 127 for char in endpoint)):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or host.endswith((".localhost", ".local")):
                raise ValueError()
        else:
            if not address.is_global:
                raise ValueError()
        return parsed
    except ValueError as exc:
        raise BadRequestError("A public HTTPS endpoint without query or credentials is required", reason="catalog_provider_endpoint") from exc


def fetch_json(endpoint: str, params: dict) -> dict:
    parsed = validate_endpoint(endpoint)
    host = parsed.hostname
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise BadRequestError("Provider address is not public", reason="catalog_provider_address")
    # Connect to the validated address, retaining hostname verification and SNI.
    conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
    raw = socket.create_connection((addresses[0][4][0], 443), timeout=TIMEOUT)
    try:
        conn.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        conn.request("GET", (parsed.path or "/") + "?" + urlencode(params),
                     headers={"Accept": "application/json", "Accept-Encoding": "identity", "User-Agent": "iCinema/1.0"})
        response = conn.getresponse()
        # Redirects are intentionally not followed (including redirects to private hosts).
        if response.status != 200:
            raise BadRequestError("Provider HTTP error", reason="catalog_provider_http")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise BadRequestError("Unexpected content encoding", reason="catalog_provider_payload")
        if int(response.getheader("Content-Length", "0")) > MAX_BYTES:
            raise BadRequestError("Provider response too large", reason="catalog_provider_payload")
        chunks, size, deadline = [], 0, time.monotonic() + TIMEOUT
        while size <= MAX_BYTES:
            if time.monotonic() >= deadline:
                raise TimeoutError("Provider read deadline exceeded")
            chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_BYTES:
            raise BadRequestError("Provider response too large", reason="catalog_provider_payload")
        data = json.loads(b"".join(chunks).decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("code") != 1 or not isinstance(data.get("list"), list):
            raise BadRequestError("Invalid provider response", reason="catalog_provider_payload")
        return data
    finally:
        conn.close()
        raw.close()


async def reserve_request(provider_id: int):
    from app.core.database import AsyncSessionLocal
    # A database reservation enforces spacing across preview requests and workers.
    while True:
        async with AsyncSessionLocal() as db:
            now = time.time()
            result = await db.execute(update(CatalogProvider).where(
                CatalogProvider.id == provider_id, CatalogProvider.next_request_at <= now,
            ).values(next_request_at=now + 1.3))
            await db.commit()
            if result.rowcount:
                return
            if await db.get(CatalogProvider, provider_id) is None:
                raise BadRequestError("Provider unavailable", reason="catalog_provider_disabled")
        await asyncio.sleep(0.3)


async def request_json(provider_id: int, endpoint: str, params: dict):
    for attempt in range(3):
        await reserve_request(provider_id)
        try:
            return await asyncio.to_thread(fetch_json, endpoint, params)
        except BadRequestError as exc:
            if exc.reason != "catalog_provider_http" or attempt == 2:
                raise
            await asyncio.sleep(1.3 * (2 ** attempt))
        except (OSError, http.client.HTTPException, ValueError, UnicodeError) as exc:
            if attempt == 2:
                raise BadRequestError("Provider request failed", reason="catalog_provider_unavailable") from exc
            await asyncio.sleep(1.3 * (2 ** attempt))
