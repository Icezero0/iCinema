import hashlib
import ipaddress
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app.core.exceptions import BadRequestError

MAX_EPISODES = 500


def invalid(reason="omofun_payload"):
    return BadRequestError("Unable to parse Omofun resource", reason=reason)


def normalize_work_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"[1-9][0-9]{0,19}", value):
        return value
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or parsed.hostname != "omofun.in"
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in {None, 80 if parsed.scheme == "http" else 443}
                or "\\" in value or any(ord(c) < 33 for c in value)):
            raise ValueError()
        match = re.fullmatch(r"/vod/(?:detail/([1-9][0-9]{0,19})\.html|play/([1-9][0-9]{0,19})(?:/(?:ep[0-9]+(?:\.[0-9]+)?)\.html|\.html|/)?)", parsed.path)
        if match:
            return match.group(1) or match.group(2)
    except ValueError:
        pass
    raise invalid("omofun_input")


class DetailParser(HTMLParser):
    def __init__(self, work_id):
        super().__init__(convert_charrefs=True)
        self.work_id = work_id
        self.title_parts = []
        self.in_title = False
        self.current = None
        self.episodes = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.in_title = True
        if tag == "a":
            self.current = None
            path = urlsplit(attrs.get("href") or "").path
            match = re.fullmatch(rf"/vod/play/{self.work_id}/(ep([0-9]+(?:\.[0-9]+)?))\.html", path)
            if match and "module-play-list-link" in (attrs.get("class") or "").split():
                self.current = [match.group(1), match.group(2), []]

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.current:
            self.current[2].append(data)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_title = False
        if tag == "a" and self.current:
            key, number, parts = self.current
            self.episodes.setdefault(key, {"id": key, "number": number, "title": "".join(parts).strip()[:200]})
            self.current = None


def parse_detail(work_id: str, html: str) -> dict:
    parser = DetailParser(work_id)
    try:
        parser.feed(html)
    except ValueError as exc:
        raise invalid() from exc
    title = "".join(parser.title_parts).strip()[:255]
    if not title or not parser.episodes:
        raise invalid("omofun_no_episodes")
    if len(parser.episodes) > MAX_EPISODES:
        raise invalid("omofun_limit")
    return {"title": title, "episodes": sorted(parser.episodes.values(), key=lambda ep: float(ep["number"]))}


def is_hls_url(value):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 33 for c in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (parsed.scheme not in {"http", "https"} or not host or parsed.username is not None
                or parsed.password is not None or not parsed.path.lower().endswith(".m3u8")):
            return False
        _ = parsed.port
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host and not host.endswith((".local", ".localhost"))
    except ValueError:
        return False


def parse_lines(payload: dict) -> dict:
    rows = payload.get("video_plays") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) > 128:
        raise invalid()
    lines, seen, skipped = [], set(), 0
    for row in rows:
        if not isinstance(row, dict):
            raise invalid()
        url, source = row.get("play_data"), row.get("src_site")
        if not isinstance(source, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", source) or not is_hls_url(url):
            skipped += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        # Identity is content-based, never the upstream array position. Rotated URLs get new IDs.
        key = hashlib.sha256((source + "\n" + url).encode()).hexdigest()[:24]
        lines.append({"id": key, "source": source, "label": source[:2].upper() + "线路", "url": url, "media_type": "hls"})
    if not lines:
        raise invalid("omofun_no_lines")
    return {"lines": lines, "skipped_lines": skipped}
