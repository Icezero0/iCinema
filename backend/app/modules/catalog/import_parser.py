import re
from decimal import Decimal
from html.parser import HTMLParser

from .playback_schemas import PlaybackInput
from .schemas import ContentInput


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value, limit):
    parser = TextOnly()
    parser.feed(str(value or ""))
    return " ".join(parser.parts).strip()[:limit]


def episode_identity(label: str):
    label = label.strip()
    match = re.search(r"第\s*(\d+(?:\.\d+)?)\s*[集话話]", label, re.I)
    if match:
        number = float(match.group(1))
        number = int(number) if number.is_integer() else number
        return ("episode", number) if number <= 99999 else None
    match = re.fullmatch(r"(?:EP\s*)?(\d+(?:\.\d+)?)(?:已?完结)?", label, re.I)
    if match:
        number = float(match.group(1))
        number = int(number) if number.is_integer() else number
        return ("episode", number) if number <= 99999 else None
    match = re.fullmatch(r"(?:SP|特别篇|特別篇|OVA|OAD)\s*(\d+)?", label, re.I)
    if match:
        number = int(match.group(1) or 1)
        return ("special", number) if number <= 99999 else None
    if label in ("正片", "电影", "電影"):
        return "movie", 1
    return None


HLS_URL = re.compile(r'''https?://[^\s<>"'$#]+?\.m3u8(?![\w./])(?:\?[^\s<>"'$#]*)?''', re.I)


def inserted_numbers(candidates, reserved):
    """Number unknown runs bounded by consecutive explicit regular episodes."""
    result = {}
    index = 0
    while index < len(candidates):
        if candidates[index][2] is not None:
            index += 1
            continue
        start = index
        while index < len(candidates) and candidates[index][2] is None:
            index += 1
        left = candidates[start - 1][2] if start else None
        right = candidates[index][2] if index < len(candidates) else None
        if not (left and right and left[0] == right[0] == 'episode'
                and float(left[1]).is_integer() and right[1] == left[1] + 1):
            continue
        count = index - start
        base = Decimal(str(left[1])) + Decimal('0.5')
        if count == 1 and ('episode', float(base)) not in reserved:
            numbers = [float(base)]
        else:
            digits = len(str(count)) + 1
            while True:
                unit = Decimal(10) ** -digits
                numbers = [float(base + n * unit) for n in range(1, 10 ** (digits - 1))
                           if ('episode', float(base + n * unit)) not in reserved][:count]
                if len(numbers) == count:
                    break
                digits += 1
        for offset, number in enumerate(numbers):
            result[start + offset] = ('episode', number)
            reserved.add(('episode', number))
    return result


def parse_detail(row: dict, category: str, play_from: str):
    year_text = str(row.get("vod_year") or "")
    year = int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None
    fields = ContentInput(title=plain(row.get("vod_name"), 255), aliases=plain(row.get("vod_sub"), 1000),
        category=category, region=plain(row.get("vod_area"), 16), content_type="tv", year=year,
        description=plain(row.get("vod_content"), 10000)).model_dump()
    groups = str(row.get("vod_play_from") or "").split("$$$")
    urls = str(row.get("vod_play_url") or "").split("$$$")
    entries, warnings, seen = [], [], set()
    if len(groups) != len(urls):
        return fields, [], ["play_groups_mismatch"]
    for line, group in zip(groups, urls):
        if line != play_from:
            warnings.append("unsupported_line")
            continue
        candidates = []
        for raw in group.split("#")[:2000]:
            match = HLS_URL.search(raw)
            label = raw[:match.start()].rstrip("$ \t") if match else raw.partition("$")[0]
            if not match:
                warnings.append("invalid_playback_url: " + plain(label, 80))
                continue
            try:
                checked = PlaybackInput(episode_id=1, line_id=1, url=match.group(), media_type="hls")
            except ValueError:
                warnings.append("invalid_playback_url: " + plain(label, 80))
                continue
            candidates.append((label, checked.url, episode_identity(label)))
        reserved = {identity for _, _, identity in candidates if identity is not None}
        inserted = inserted_numbers(candidates, reserved)
        for position, (label, url, identity) in enumerate(candidates, 1):
            identity = identity or inserted.get(position - 1)
            if identity is None:
                number = position
                while ("episode", number) in reserved or f"{line}|episode|{number}" in seen:
                    number += 1
                identity = ("episode", number)
                if number != position:
                    warnings.append("episode_number_adjusted: " + plain(label, 80))
            key = f"{line}|{identity[0]}|{identity[1]}"
            if key in seen:
                warnings.append("duplicate_episode: " + plain(label, 80))
                continue
            seen.add(key)
            entries.append(dict(key=key, line=line, kind=identity[0], number=identity[1],
                                title=plain(label, 255) or str(identity[1]), url=url))
        if len(group.split("#")) > 2000:
            warnings.append("episode_limit")
    if entries and all(entry["kind"] == "movie" for entry in entries):
        fields["content_type"] = "movie"
    return fields, entries, warnings[:30]
