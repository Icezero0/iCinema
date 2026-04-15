import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
from urllib.request import urlopen

from app.core.config import get_settings
from app.modules.media.constants import EmojiProvider

settings = get_settings()


def _download_text(url: str, timeout: int) -> str:
    with urlopen(url, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8")


class EmojiCatalogService:
    def __init__(self) -> None:
        self._items: list[dict] = []
        self._item_map: dict[str, dict] = {}
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def _fetch_catalog(self) -> tuple[list[dict], dict[str, dict]]:
        text = await asyncio.to_thread(
            _download_text,
            settings.emoji_catalog_url,
            settings.emoji_catalog_timeout_seconds,
        )
        raw = json.loads(text)

        if not isinstance(raw, list):
            raise ValueError("Emoji catalog root must be a list")

        items: list[dict] = []
        item_map: dict[str, dict] = {}

        for row in raw:
            emoji_id = str(row.get("emojiId") or "").strip()
            is_hide = bool(row.get("isHide", False))
            raw_assets = row.get("assets") or []

            if not emoji_id:
                continue
            if is_hide:
                continue
            if not raw_assets:
                continue

            assets: list[dict] = []
            for asset in raw_assets:
                path = str(asset.get("path") or "").strip()
                if not path:
                    continue

                assets.append(
                    {
                        "type": int(asset.get("type", 0)),
                        "name": str(asset.get("name") or ""),
                        "path": path,
                        "url": urljoin(settings.emoji_public_base_url.rstrip("/") + "/", path.lstrip("/")),
                    }
                )

            if not assets:
                continue

            item = {
                "provider": EmojiProvider.QFACE,
                "id": emoji_id,
                "describe": row.get("describe") or None,
                "assets": assets,
            }
            items.append(item)
            item_map[emoji_id] = item

        return items, item_map

    async def _ensure_loaded(self) -> None:
        now = datetime.now(timezone.utc)

        if self._expires_at is not None and now < self._expires_at and self._items:
            return

        async with self._lock:
            now = datetime.now(timezone.utc)
            if self._expires_at is not None and now < self._expires_at and self._items:
                return

            try:
                items, item_map = await self._fetch_catalog()
                self._items = items
                self._item_map = item_map
                self._expires_at = now + timedelta(seconds=settings.emoji_catalog_cache_ttl_seconds)
            except Exception:
                if self._items:
                    self._expires_at = now + timedelta(seconds=60)
                    return
                raise

    async def get_visible_emojis(self) -> list[dict]:
        await self._ensure_loaded()
        return list(self._items)

    async def get_emoji(self, emoji_id: str) -> dict | None:
        await self._ensure_loaded()
        return self._item_map.get(emoji_id)