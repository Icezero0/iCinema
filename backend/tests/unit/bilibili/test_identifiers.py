import pytest

from app.modules.bilibili.identifiers import BilibiliVideoRef, parse_bilibili_ref


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BV1Wneiz5EpD", BilibiliVideoRef("BV1Wneiz5EpD", 1)),
        (" https://www.bilibili.com/video/BV1Wneiz5EpD/?p=3&spm_id_from=333.1007 ",
         BilibiliVideoRef("BV1Wneiz5EpD", 3)),
        ("https://m.bilibili.com/video/BV1Wneiz5EpD", BilibiliVideoRef("BV1Wneiz5EpD", 1)),
    ],
)
def test_parse_bilibili_video_reference(value, expected):
    assert parse_bilibili_ref(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "BV1Wneiz5Ep",
        "https://www.bilibili.com.evil.example/video/BV1Wneiz5EpD",
        "https://www.bilibili.com@evil.example/video/BV1Wneiz5EpD",
        "https://www.bilibili.com:8443/video/BV1Wneiz5EpD",
        "https://www.bilibili.com/video/BV1Wneiz5EpD?p=0",
        "https://www.bilibili.com/video/BV1Wneiz5EpD?p=2&p=3",
        "https://www.bilibili.com/video/BV1Wneiz5EpD?p=1001",
        "https://www.bilibili.com/video/BV1Wneiz5EpD/extra",
        "https://b23.tv/example",
    ],
)
def test_reject_invalid_video_reference(value):
    with pytest.raises(ValueError):
        parse_bilibili_ref(value)
