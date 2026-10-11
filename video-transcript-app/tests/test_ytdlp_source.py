"""yt-dlp integration. The download steps run the real yt-dlp library against a
local HTTP server, so they prove the wiring without touching YouTube/TikTok."""

import os

import pytest

from app import ytdlp_source
from app.models import (
    NoTranscriptAvailable,
    SpeechToTextRefused,
    UpstreamBlocked,
    UpstreamError,
    VideoMeta,
    VideoUnavailable,
)
from app.urls import VideoRef
from app.ytdlp_source import VideoInfo, _collect_tracks, _map_error

from conftest import fixture_text


def yt_entries(base, extra=""):
    return [
        {"ext": ext, "url": f"https://www.youtube.com/api/timedtext?v=x&lang={base}{extra}&fmt={ext}", "name": "English"}
        for ext in ("json3", "srv1", "srv2", "srv3", "ttml", "srt", "vtt")
    ]


def test_youtube_tracks_keep_manual_and_original_auto_only():
    info = {
        "subtitles": {"en": yt_entries("en"), "live_chat": [{"ext": "json", "url": "x"}]},
        "automatic_captions": {
            "en-orig": [{**e, "name": "English (Original)"} for e in yt_entries("en")],
            "en": yt_entries("en"),
            "de": [{**e, "name": "German"} for e in yt_entries("en", "&tlang=de")],
            "fr": [{**e, "name": "French"} for e in yt_entries("en", "&tlang=fr")],
        },
    }
    tracks, keys = _collect_tracks(info, "youtube")
    assert [(t.code, t.kind, t.name, t.is_original) for t in tracks] == [
        ("en", "manual", "English", False),
        ("a.en", "auto", "English (auto-generated)", True),
    ]
    assert keys == {"en": ("en", False), "a.en": ("en-orig", True)}


def test_tiktok_tracks_skip_unparseable_formats():
    info = {
        "subtitles": {
            "eng-US": [{"ext": "srt", "data": "1\n00:00:00,000 --> 00:00:01,000\nhi\n"}],
            "spa-ES": [{"ext": "json", "url": "https://x/1"}, {"ext": "vtt", "url": "https://x/2"}],
            "fra-FR": [{"ext": "json", "url": "https://x/3"}],  # creator_caption JSON only
        }
    }
    tracks, keys = _collect_tracks(info, "tiktok")
    assert [t.code for t in tracks] == ["a.eng-US", "a.spa-ES"]
    assert all(t.kind == "auto" for t in tracks)


def make_video(subtitles=None, formats=None, platform="tiktok"):
    raw = {
        "id": "7106798200794926362",
        "title": "test video",
        "extractor": "TikTok",
        "extractor_key": "TikTok",
        "webpage_url": "https://www.tiktok.com/@u/video/7106798200794926362",
        "formats": formats or [],
        "subtitles": subtitles or {},
        "automatic_captions": {},
    }
    tracks, keys = _collect_tracks(raw, platform)
    return VideoInfo(
        platform=platform,
        video_id=raw["id"],
        url=raw["webpage_url"],
        meta=VideoMeta(),
        tracks=tracks,
        raw=raw,
        caption_keys=keys,
    )


def test_inline_caption_data_needs_no_download(settings):
    video = make_video({"eng-US": [{"ext": "srt", "data": fixture_text("tiktok.srt")}]})
    segments = ytdlp_source.download_captions(video, video.tracks[0], settings)
    assert [s.text for s in segments] == ["POV: you finally", "found the perfect coffee", "shop"]


def test_caption_download_through_real_ytdlp(settings, local_server):
    local_server.routes["/subs.vtt"] = fixture_text("youtube_auto_rolling.vtt").encode()
    local_server.routes["/subs.json"] = b'{"never": "requested"}'
    video = make_video(
        {
            "spa-ES": [
                {"ext": "json", "url": local_server.base_url + "/subs.json"},
                {"ext": "vtt", "url": local_server.base_url + "/subs.vtt"},
            ]
        }
    )
    segments = ytdlp_source.download_captions(video, video.tracks[0], settings)
    assert [s.text for s in segments][:2] == ["hey everyone welcome back", "to the channel today"]
    assert local_server.hits == ["/subs.vtt"]  # the unparseable format was never fetched


def test_caption_download_failure_is_reported(settings, local_server):
    video = make_video({"eng-US": [{"ext": "vtt", "url": local_server.base_url + "/missing.vtt"}]})
    with pytest.raises(UpstreamError):
        ytdlp_source.download_captions(video, video.tracks[0], settings)


def test_track_with_no_parseable_format(settings):
    video = make_video({"eng-US": [{"ext": "vtt", "url": "https://x/1"}]})
    video.raw["subtitles"]["eng-US"] = [{"ext": "ttml", "url": "https://x/1"}]
    with pytest.raises(NoTranscriptAvailable):
        ytdlp_source.download_captions(video, video.tracks[0], settings)


def audio_format(url):
    return {"format_id": "audio", "url": url, "ext": "m4a", "acodec": "mp4a.40.2", "vcodec": "none", "protocol": "http"}


def test_audio_download_through_real_ytdlp(settings, local_server, tmp_path):
    local_server.routes["/audio.m4a"] = b"\x00" * 4096
    video = make_video(formats=[audio_format(local_server.base_url + "/audio.m4a")])
    path = ytdlp_source.download_audio(video, str(tmp_path), settings)
    assert os.path.dirname(path) == str(tmp_path)
    assert os.path.getsize(path) == 4096


def test_audio_over_size_limit_is_refused(local_server, tmp_path):
    from app.config import Settings

    local_server.routes["/audio.m4a"] = b"\x00" * 50_000
    video = make_video(formats=[audio_format(local_server.base_url + "/audio.m4a")])
    small = Settings(cache_ttl_seconds=0, whisper_max_download_bytes=10_000)
    with pytest.raises(SpeechToTextRefused):
        ytdlp_source.download_audio(video, str(tmp_path), small)


def test_generic_extractor_is_disabled(settings, local_server):
    """Even if a non-YouTube/TikTok URL slipped past validation, yt-dlp must not fetch it."""
    local_server.routes["/video.mp4"] = b"\x00" * 100
    ref = VideoRef("tiktok", "x", local_server.base_url + "/video.mp4")
    with pytest.raises(UpstreamError):
        ytdlp_source.extract(ref, settings)
    assert local_server.hits == []


@pytest.mark.parametrize(
    "message, expected",
    [
        ("ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies", UpstreamBlocked),
        ("ERROR: [TikTok] 123: Your IP address is blocked from accessing this post", UpstreamBlocked),
        ("ERROR: unable to download webpage: HTTP Error 429: Too Many Requests", UpstreamBlocked),
        ("ERROR: [youtube] abc: Video unavailable. This video is private", VideoUnavailable),
        ("ERROR: [youtube] abc: Private video. Sign in if you've been granted access", VideoUnavailable),
        ("ERROR: [TikTok] 123: Unable to extract webpage video data", UpstreamError),
    ],
)
def test_error_mapping(message, expected):
    err = _map_error(Exception(message), "youtube")
    assert isinstance(err, expected)
    assert not err.details[0].startswith("ERROR")


def test_error_details_drop_ytdlp_bug_report_boilerplate():
    err = _map_error(
        Exception(
            "ERROR: [TikTok] 1: Unable to download webpage: timed out; please report this issue on "
            " https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template."
        ),
        "tiktok",
    )
    assert err.details == ["Unable to download webpage: timed out"]


@pytest.mark.parametrize(
    "webpage_url, expected",
    [
        ("https://www.tiktok.com/@real.user/video/7106798200794926362", "https://www.tiktok.com/@real.user/video/7106798200794926362"),
        ("javascript:alert(1)", "https://vm.tiktok.com/ZTR45GpSF/"),
        ("https://evil.test/@u/video/7106798200794926362", "https://vm.tiktok.com/ZTR45GpSF/"),
    ],
)
def test_extract_only_trusts_valid_page_urls(monkeypatch, settings, webpage_url, expected):
    def fake_extract_info(self, url, download=False):
        return {"id": "7106798200794926362", "title": "t", "webpage_url": webpage_url, "duration": 12, "subtitles": {}}

    monkeypatch.setattr(ytdlp_source.yt_dlp.YoutubeDL, "extract_info", fake_extract_info)
    video = ytdlp_source.extract(VideoRef("tiktok", "ZTR45GpSF", "https://vm.tiktok.com/ZTR45GpSF/", True), settings)
    assert video.url == expected
    assert video.video_id == "7106798200794926362"
    assert video.meta.duration == 12.0
