import pytest

from app.core.exceptions import BadRequestError
from app.modules.omofun.parser import normalize_work_id, parse_detail, parse_lines
from app.modules.omofun import client


@pytest.mark.parametrize("value", ["2019219963", "https://omofun.in/vod/play/2019219963",
    "https://omofun.in/vod/play/2019219963/ep1.html", "https://omofun.in/vod/detail/2019219963.html?x=1"])
def test_normalize(value):
    assert normalize_work_id(value) == "2019219963"


@pytest.mark.parametrize("value", ["0", "../../1", "https://omofun.in.evil.test/vod/play/1",
    "https://user@omofun.in/vod/play/1", "https://omofun.in:444/vod/play/1", "http://127.0.0.1/1",
    "https://omofun.in/vod/search.html?wd=test", "https://omofun.in/vod/play/1/../../admin"])
def test_invalid_input(value):
    with pytest.raises(BadRequestError):
        normalize_work_id(value)


def test_detail_uses_episode_list_not_promoted_latest_link():
    html = '''<h1>A &amp; B</h1><a href="/vod/play/1/ep26.html">Play now</a>
    <a class="module-play-list-link" href="/vod/play/1/ep2.html"><span>2</span></a>
    <a class="module-play-list-link" href="/vod/play/1/ep1.html">1</a>
    <a class="module-play-list-link" href="/vod/play/1/ep1.html">Duplicate</a>
    <a class="module-play-list-link" href="/vod/play/2/ep3.html">Other work</a>'''
    data = parse_detail("1", html)
    assert data["title"] == "A & B"
    assert [ep["id"] for ep in data["episodes"]] == ["ep1", "ep2"]
    with pytest.raises(BadRequestError):
        parse_detail("1", "<h1>Captcha</h1>")


def test_detail_extracts_only_work_poster_and_plain_introduction():
    html = '''<img src="/logo.png"><h1>Test</h1>
    <div class="module-info-poster"><a><img data-original="/cover.jpg" src="/loading.gif"></a></div>
    <div class="module-info-introduction-content"><p>First &amp; second<br>Next <b>line</b></p><script>ignored()</script></div>
    <div>Director and other metadata</div><img src="/recommendation.jpg">
    <a class="module-play-list-link" href="/vod/play/1/ep1.html">1</a>'''
    result = parse_detail("1", html)
    assert result["poster_url"] == "https://omofun.in/cover.jpg"
    assert result["description"] == "First & second Next line"
    missing = parse_detail("1", '<h1>Test</h1><a class="module-play-list-link" href="/vod/play/1/ep1.html">1</a>')
    assert missing["poster_url"] is None and missing["description"] == ""


def test_work_metadata_uses_labels_and_ignores_scripts_and_recommendations():
    html = '''<h1>Test</h1><div class="module-info-main">
      <div class="module-info-item"><span class="module-info-item-title">备注：</span><div class="module-info-item-content">更新至第24集</div></div>
      <div class="module-info-item"><span class="module-info-item-title">导演：</span><div class="module-info-item-content"><a>Director A</a><span>/</span></div></div>
      <div class="module-info-item"><span class="module-info-item-title">主演：</span><div class="module-info-item-content"><a>Actor A</a><span>/</span><a>Actor B</a><span>/</span><script>bad()</script></div></div>
      <div class="module-info-item"><span class="module-info-item-title">更新：</span><div class="module-info-item-content">2024年3月24日 11:47</div></div>
    </div><div class="module-info-item"><span class="module-info-item-title">导演：</span><div class="module-info-item-content">Wrong</div></div>
    <a class="module-play-list-link" href="/vod/play/1/ep1.html">1</a>'''
    result = parse_detail("1", html)
    assert result["director"] == "Director A"
    assert result["cast"] == "Actor A/Actor B"
    assert result["updated_text"] == "2024年3月24日 11:47"
    assert result["remarks"] == "更新至第24集"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:image/svg+xml,x", "http://127.0.0.1/p.jpg", "https://user:pass@host.test/p.jpg"])
def test_detail_ignores_unsafe_poster(url):
    html = f'<h1>Test</h1><div class="module-info-poster"><img src="{url}"></div><a class="module-play-list-link" href="/vod/play/1/ep1.html">1</a>'
    assert parse_detail("1", html)["poster_url"] is None


def test_lines_preserve_same_source_variants_and_signed_queries():
    first = {"src_site": "ffzy", "play_data": "https://video.example/a.m3u8?sign=123"}
    second = {"src_site": "ffzy", "play_data": "https://video.example/b.m3u8"}
    rows = [first, first, second, {"src_site": "x", "play_data": "https://video.example/player.html"}]
    result = parse_lines({"video_plays": rows})
    assert len(result["lines"]) == 2 and result["skipped_lines"] == 1
    assert result["lines"][0]["url"].endswith("?sign=123")
    assert result["lines"][0]["label"] == "FF线路"
    reversed_lines = parse_lines({"video_plays": [second, first]})["lines"]
    assert result["lines"][0]["id"] == reversed_lines[1]["id"]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://127.0.0.1/a.m3u8", "https://x.local/a.m3u8", "https://u:p@host.test/a.m3u8"])
def test_unsafe_line_urls_rejected(url):
    with pytest.raises(BadRequestError):
        parse_lines({"video_plays": [{"src_site": "x", "play_data": url}]})


def test_transport_rejects_private_dns_before_connection(monkeypatch):
    monkeypatch.setattr(client.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, '', ('127.0.0.1', 443))])
    monkeypatch.setattr(client.socket, "create_connection", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(BadRequestError, match="Unable to parse"):
        client.fetch_text("/vod/detail/1.html")


@pytest.mark.parametrize("status,headers", [(302, {}), (200, {"Content-Encoding": "gzip"}),
    (200, {"Content-Length": str(client.MAX_BYTES + 1)})])
def test_transport_rejects_redirect_encoding_and_oversize(monkeypatch, status, headers):
    from unittest.mock import MagicMock
    monkeypatch.setattr(client.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, '', ('8.8.8.8', 443))])
    monkeypatch.setattr(client.socket, "create_connection", lambda *a, **k: MagicMock())
    monkeypatch.setattr(client.ssl, "create_default_context", MagicMock())
    response = MagicMock()
    response.status = status
    response.getheader.side_effect = lambda key, default=None: headers.get(key, default)
    connection = MagicMock()
    connection.getresponse.return_value = response
    monkeypatch.setattr(client.http.client, "HTTPSConnection", lambda *a, **k: connection)
    with pytest.raises(BadRequestError):
        client.fetch_text("/vod/detail/1.html")
    response.read1.assert_not_called()
    connection.close.assert_called_once()
