"""Parse a public Bilibili video reference without making a network request."""

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, urlsplit


_BVID = re.compile(r"BV[0-9A-Za-z]{10}\Z")
_ALLOWED_HOSTS = frozenset({"bilibili.com", "www.bilibili.com", "m.bilibili.com"})
_MAX_INPUT_LENGTH = 512
_MAX_PAGE = 1000


@dataclass(frozen=True, slots=True)
class BilibiliVideoRef:
    bvid: str
    page: int = 1


def parse_bilibili_ref(value: str) -> BilibiliVideoRef:
    """Accept a BV ID or an ordinary /video/BV... URL.

    Short links must be resolved by a separate, explicitly restricted service.
    No arbitrary URL is fetched here.
    """
    if not isinstance(value, str):
        raise ValueError("invalid_bilibili_reference")
    value = value.strip()
    if not value or len(value) > _MAX_INPUT_LENGTH or any(char.isspace() for char in value):
        raise ValueError("invalid_bilibili_reference")

    if _BVID.fullmatch(value):
        return BilibiliVideoRef(bvid=value)

    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid_bilibili_reference") from exc

    if (
        parsed.scheme not in {"http", "https"}
        or host not in _ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise ValueError("invalid_bilibili_reference")

    parts = parsed.path.rstrip("/").split("/")
    if len(parts) != 3 or parts[0] != "" or parts[1] != "video" or not _BVID.fullmatch(parts[2]):
        raise ValueError("invalid_bilibili_reference")

    query = parse_qs(parsed.query, keep_blank_values=True)
    pages = query.get("p")
    if pages is None:
        page = 1
    elif len(pages) == 1 and pages[0].isascii() and pages[0].isdecimal():
        page = int(pages[0])
        if not 1 <= page <= _MAX_PAGE:
            raise ValueError("invalid_bilibili_page")
    else:
        raise ValueError("invalid_bilibili_page")

    return BilibiliVideoRef(bvid=parts[2], page=page)
