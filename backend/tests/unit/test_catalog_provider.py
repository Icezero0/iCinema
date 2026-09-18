import json
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BadRequestError
from app.modules.catalog import provider_client as client
from app.modules.catalog.import_parser import episode_identity, parse_detail


@pytest.mark.parametrize("label,expected", [("第01集", ("episode", 1)), ("EP03", ("episode", 3)),
    ("12", ("episode", 12)), ("特别篇", ("special", 1)), ("SP2", ("special", 2)),
    ("正片", ("movie", 1)), ("第1-2集", None), ("第3集上", ("episode", 3)),
    ("第1集完结", ("episode", 1)), ("第50集已完结", ("episode", 50)),
    ("预告", None), ("100000", None)])
def test_episode_identity_extracts_explicit_number(label, expected):
    assert episode_identity(label) == expected


def test_parser_preserves_title_and_rejects_group_mismatch():
    fields, entries, warnings = parse_detail(dict(vod_name="测试 第二季", vod_year="未知",
        vod_content="<p>介绍</p>", vod_play_from="jinyingm3u8$$$other", vod_play_url="第1集$https://example.test/a.m3u8"), "japanese_animation", "jinyingm3u8")
    assert fields["title"] == "测试 第二季" and fields["year"] is None and fields["description"] == "介绍"
    assert not entries and warnings == ["play_groups_mismatch"]


def parsed(raw):
    return parse_detail(dict(vod_name="测试", vod_play_from="jinyingm3u8", vod_play_url=raw),
                        "japanese_animation", "jinyingm3u8")


def test_hls_extracted_first_with_status_labels_and_signed_query():
    _, entries, warnings = parsed('第1集完结$https://example.test/one.m3u8#第50集已完结$https://example.test/fifty.m3u8?token=abc&expires=123')
    assert [e['number'] for e in entries] == [1, 50]
    assert entries[1]['url'] == 'https://example.test/fifty.m3u8?token=abc&expires=123'
    assert not warnings


def test_no_label_or_unknown_label_uses_valid_link_order():
    _, entries, warnings = parsed('invalid$javascript:alert(1)#https://example.test/a.m3u8#花絮上$https://example.test/b.m3u8#第1-2集$https://example.test/c.m3u8')
    assert [e['number'] for e in entries] == [1, 2, 3]
    assert len(warnings) == 1 and warnings[0].startswith('invalid_playback_url:')


def test_fallback_reserves_explicit_numbers_and_does_not_overwrite_duplicates():
    _, entries, warnings = parsed('未知$https://example.test/a.m3u8#第1集$https://example.test/b.m3u8#第1集已完结$https://example.test/c.m3u8')
    assert [e['number'] for e in entries] == [2, 1]
    assert entries[1]['url'] == 'https://example.test/b.m3u8'
    assert [w.split(':')[0] for w in warnings] == ['episode_number_adjusted', 'duplicate_episode']


@pytest.mark.parametrize('url', ['https://example.test/a.mp4', 'https://example.test/a.m3u8.exe', 'https://user:pass@example.test/a.m3u8'])
def test_hls_extraction_rejects_non_hls_and_invalid_urls(url):
    _, entries, warnings = parsed('第1集$' + url)
    assert not entries and warnings[0].startswith('invalid_playback_url:')


def test_real_zzz_label_pattern_keeps_all_fifty_episodes():
    raw = '#'.join(f'第{i}集{"已完结" if i == 50 else ""}$https://example.test/{i}.m3u8' for i in range(1, 51))
    _, entries, warnings = parsed(raw)
    assert [e['number'] for e in entries] == list(range(1, 51))
    assert not warnings


@pytest.mark.parametrize('labels,expected', [
    (['第12集', '总集篇', '第13集'], [12, 12.5, 13]),
    (['第12集', '总集篇上', '总集篇下', '第13集'], [12, 12.51, 12.52, 13]),
    (['第12.5集', 'EP12.51'], [12.5, 12.51]),
    (['第0集', '回顾', '第1集'], [0, 0.5, 1]),
    (['未知', '第2集'], [1, 2]),
    (['第1集', '未知'], [1, 2]),
])
def test_inserted_episodes_use_fractional_numbers(labels, expected):
    raw = '#'.join(f'{label}$https://example.test/{i}.m3u8' for i, label in enumerate(labels))
    _, entries, warnings = parsed(raw)
    assert [e['number'] for e in entries] == expected
    assert not warnings


def test_many_insertions_stay_ordered_and_unique():
    labels = ['第12集'] + ['回顾'] * 12 + ['第13集']
    _, entries, warnings = parsed('#'.join(f'{label}$https://example.test/{i}.m3u8' for i, label in enumerate(labels)))
    numbers = [e['number'] for e in entries]
    assert numbers == sorted(set(numbers)) and len(numbers) == 14
    assert all(12 < n < 13 for n in numbers[1:-1])
    assert not warnings


def test_inserted_number_does_not_overwrite_an_explicit_fraction():
    _, entries, _ = parsed('第12集$https://example.test/a.m3u8#回顾$https://example.test/b.m3u8#第13集$https://example.test/c.m3u8#第12.5集$https://example.test/d.m3u8')
    assert [e['number'] for e in entries] == [12, 12.51, 13, 12.5]


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fe80::1"])
def test_transport_rejects_private_dns_before_connect(monkeypatch, address):
    monkeypatch.setattr(client.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", (address, 443))])
    with pytest.raises(BadRequestError) as exc:
        client.fetch_json(client.ENDPOINT, {"ac":"list"})
    assert exc.value.reason == "catalog_provider_address"


@pytest.mark.parametrize("endpoint", ["http://example.test/api", "https://127.0.0.1/api", "https://localhost/api", "https://user:pass@example.test/api", "https://example.test/api?ac=detail", "https://example.test:8080/api"])
def test_transport_rejects_unsafe_endpoint(endpoint):
    with pytest.raises(BadRequestError) as exc:
        client.fetch_json(endpoint, {})
    assert exc.value.reason == "catalog_provider_endpoint"


@pytest.mark.parametrize("status,body,headers,ok", [
    (200, b'{"code":1,"list":[]}', {"Content-Type":"text/html"}, True),
    (302, b'', {"Location":"http://127.0.0.1"}, False),
    (200, b'<html>captcha</html>', {}, False),
    (200, b'{"code":0,"list":[]}', {}, False),
    (200, b'{"code":1,"list":[]}', {"Content-Length":str(client.MAX_BYTES+1)}, False),
    (200, b'{"code":1,"list":[]}', {"Content-Encoding":"gzip"}, False),
])
@pytest.mark.parametrize("endpoint", [client.ENDPOINT, "https://catalog.example.test/api/videos/"])
def test_transport_payload_and_redirect_boundaries(monkeypatch, status, body, headers, ok, endpoint):
    class Sock:
        def close(self): pass

    class Context:
        def wrap_socket(self, raw, server_hostname):
            assert server_hostname == client.urlsplit(endpoint).hostname
            return raw

    class Response:
        def __init__(self): self.status, self.body = status, body
        def getheader(self, key, default=None): return headers.get(key, default)
        def read1(self, size):
            chunk, self.body = self.body[:size], self.body[size:]
            return chunk

    class Connection:
        def __init__(self, host, timeout): assert host == client.urlsplit(endpoint).hostname
        def request(self, method, path, headers): assert method == "GET" and path == client.urlsplit(endpoint).path + "?ac=list"
        def getresponse(self): return Response()
        def close(self): pass

    monkeypatch.setattr(client.socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("8.8.8.8", 443))])
    def connect(address, timeout):
        assert address == ("8.8.8.8", 443)  # Validated IP, not another DNS resolution.
        return Sock()
    monkeypatch.setattr(client.socket, "create_connection", connect)
    monkeypatch.setattr(client.ssl, "create_default_context", Context)
    monkeypatch.setattr(client.http.client, "HTTPSConnection", Connection)
    if ok:
        assert client.fetch_json(endpoint, {"ac":"list"}) == {"code":1,"list":[]}
    else:
        with pytest.raises((BadRequestError, json.JSONDecodeError)):
            client.fetch_json(endpoint, {"ac":"list"})


async def test_network_retry_is_bounded(monkeypatch):
    calls = []
    def fail(*args):
        calls.append(1)
        raise TimeoutError()
    monkeypatch.setattr(client, "reserve_request", AsyncMock())
    monkeypatch.setattr(client.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(client, "fetch_json", fail)
    with pytest.raises(BadRequestError) as exc:
        await client.request_json(1, client.ENDPOINT, {})
    assert exc.value.reason == "catalog_provider_unavailable" and len(calls) == 3


@pytest.mark.parametrize("failure", [TimeoutError(), BadRequestError("HTTP error", reason="catalog_provider_http")])
async def test_provider_recovers_after_two_transient_failures(monkeypatch, failure):
    calls = []
    def fetch(*args):
        calls.append(1)
        if len(calls) < 3:
            raise failure
        return {"code": 1, "list": []}
    sleep = AsyncMock()
    monkeypatch.setattr(client, "reserve_request", AsyncMock())
    monkeypatch.setattr(client.asyncio, "sleep", sleep)
    monkeypatch.setattr(client, "fetch_json", fetch)
    assert await client.request_json(1, client.ENDPOINT, {}) == {"code": 1, "list": []}
    assert len(calls) == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1.3, 2.6]


async def test_provider_does_not_retry_unsafe_address(monkeypatch):
    from unittest.mock import Mock
    fetch = Mock(side_effect=BadRequestError("Unsafe address", reason="catalog_provider_address"))
    monkeypatch.setattr(client, "reserve_request", AsyncMock())
    monkeypatch.setattr(client, "fetch_json", fetch)
    with pytest.raises(BadRequestError):
        await client.request_json(1, client.ENDPOINT, {})
    assert fetch.call_count == 1
