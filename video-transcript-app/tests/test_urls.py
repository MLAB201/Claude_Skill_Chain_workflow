import pytest

from app.models import InvalidVideoUrl
from app.urls import parse_video_url

YT = "dQw4w9WgXcQ"
TT = "6718335390845095173"


@pytest.mark.parametrize(
    "raw",
    [
        f"https://www.youtube.com/watch?v={YT}",
        f"https://youtube.com/watch?v={YT}&t=42s&list=PL1234567890",
        f"https://m.youtube.com/watch?feature=share&v={YT}",
        f"https://music.youtube.com/watch?v={YT}",
        f"https://youtu.be/{YT}?si=abcdef",
        f"https://www.youtube.com/shorts/{YT}",
        f"https://www.youtube.com/live/{YT}?feature=share",
        f"https://www.youtube.com/embed/{YT}",
        f"https://www.youtube-nocookie.com/embed/{YT}",
        f"youtube.com/watch?v={YT}",
        f"  https://www.youtube.com/watch?v={YT}  ",
        f"HTTPS://WWW.YOUTUBE.COM/watch?v={YT}",
        f"http://www.youtube.com:443/watch?v={YT}",
        YT,
    ],
)
def test_youtube_urls(raw):
    ref = parse_video_url(raw)
    assert ref.platform == "youtube"
    assert ref.video_id == YT
    assert ref.url == f"https://www.youtube.com/watch?v={YT}"
    assert not ref.is_short_link


@pytest.mark.parametrize(
    "raw, canonical",
    [
        (f"https://www.tiktok.com/@scout2015/video/{TT}", f"https://www.tiktok.com/@scout2015/video/{TT}"),
        (
            f"https://www.tiktok.com/@scout2015/video/{TT}?is_from_webapp=1&sender_device=pc",
            f"https://www.tiktok.com/@scout2015/video/{TT}",
        ),
        (f"https://www.tiktok.com/@we%20ird/video/{TT}", f"https://www.tiktok.com/@_/video/{TT}"),
        (f"https://m.tiktok.com/v/{TT}.html", f"https://www.tiktok.com/@_/video/{TT}"),
        (f"https://www.tiktok.com/embed/v2/{TT}", f"https://www.tiktok.com/@_/video/{TT}"),
        (f"tiktok.com/@scout2015/video/{TT}", f"https://www.tiktok.com/@scout2015/video/{TT}"),
    ],
)
def test_tiktok_urls(raw, canonical):
    ref = parse_video_url(raw)
    assert ref.platform == "tiktok"
    assert ref.video_id == TT
    assert ref.url == canonical


@pytest.mark.parametrize(
    "raw, canonical",
    [
        ("https://vm.tiktok.com/ZTR45GpSF/", "https://vm.tiktok.com/ZTR45GpSF/"),
        ("https://vt.tiktok.com/ZSabc123/", "https://vt.tiktok.com/ZSabc123/"),
        ("https://www.tiktok.com/t/ZTRC5xgJp/", "https://www.tiktok.com/t/ZTRC5xgJp/"),
    ],
)
def test_tiktok_short_links(raw, canonical):
    ref = parse_video_url(raw)
    assert ref.platform == "tiktok"
    assert ref.is_short_link
    assert ref.url == canonical


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        f"https://example.com/watch?v={YT}",
        f"https://youtube.com.evil.test/watch?v={YT}",
        f"https://evil.test/?u=https://youtube.com/watch?v={YT}",
        f"https://www.youtube.com@evil.test/watch?v={YT}",
        f"https://evil.test#@www.youtube.com/watch?v={YT}",
        "javascript:alert(1)",
        f"ftp://www.youtube.com/watch?v={YT}",
        "file:///etc/passwd",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/playlist?list=PL1234567890",
        "https://www.youtube.com/@somechannel",
        "https://youtu.be/",
        "https://www.tiktok.com/@scout2015",
        "https://www.tiktok.com/@scout2015/photo/7300000000000000000",
        "https://www.tiktok.com/@scout2015/video/notanumber",
        "https://vm.tiktok.com/",
        "https://[broken",
        "https://www.youtube.com/watch?v=" + "a" * 3000,
    ],
)
def test_rejected_urls(raw):
    with pytest.raises(InvalidVideoUrl):
        parse_video_url(raw)


def test_rejection_names_the_host():
    with pytest.raises(InvalidVideoUrl) as info:
        parse_video_url("https://vimeo.com/123")
    assert "vimeo.com" in info.value.details[0]
