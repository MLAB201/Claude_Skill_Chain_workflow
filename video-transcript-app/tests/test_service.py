"""The fallback pipeline, with each source replaced by a stub."""

import pytest

from app import service as service_mod
from app.config import Settings
from app.models import (
    NoTranscriptAvailable,
    Segment,
    SpeechToTextBusy,
    SpeechToTextRefused,
    TrackInfo,
    UpstreamBlocked,
    VideoMeta,
)
from app.service import TranscriptService
from app.urls import parse_video_url
from app.ytdlp_source import VideoInfo

YT = parse_video_url("https://youtu.be/dQw4w9WgXcQ")
TT = parse_video_url("https://www.tiktok.com/@u/video/7106798200794926362")
SEGMENTS = [Segment(0.0, 1.5, "hello there"), Segment(1.5, 3.0, "general kenobi")]
EN = TrackInfo(code="en", language="en", name="English", kind="manual")
AUTO_EN = TrackInfo(code="a.en", language="en", name="English (auto-generated)", kind="auto", is_original=True)


class Calls:
    def __init__(self):
        self.log = []


@pytest.fixture
def calls(monkeypatch):
    c = Calls()
    monkeypatch.setattr(service_mod.speech, "is_available", lambda s: False)
    monkeypatch.setattr(
        service_mod.youtube_api, "fetch_metadata", lambda vid, s: VideoMeta(title="T", author="A")
    )
    return c


def stub_youtube_api(monkeypatch, calls, result=None, error=None):
    def fake(video_id, requested, settings):
        calls.log.append(("youtube_api", requested))
        if error:
            raise error
        return result

    monkeypatch.setattr(service_mod.youtube_api, "fetch", fake)


def stub_ytdlp(monkeypatch, calls, tracks=(), segments=SEGMENTS, platform="youtube", duration=60.0, error=None):
    def fake_extract(ref, settings):
        calls.log.append(("ytdlp_extract", ref.video_id))
        if error:
            raise error
        return VideoInfo(
            platform=platform,
            video_id=ref.video_id,
            url=ref.url,
            meta=VideoMeta(title="T", duration=duration),
            tracks=list(tracks),
            raw={},
            caption_keys={t.code: (t.language, t.kind == "auto") for t in tracks},
            warnings=["WARNING: [youtube] x: Some subtitles need a PO token"],
        )

    def fake_download(video, track, settings):
        calls.log.append(("ytdlp_captions", track.code))
        return list(segments)

    monkeypatch.setattr(service_mod.ytdlp_source, "extract", fake_extract)
    monkeypatch.setattr(service_mod.ytdlp_source, "download_captions", fake_download)


def stub_speech(monkeypatch, calls, segments=SEGMENTS):
    monkeypatch.setattr(service_mod.speech, "is_available", lambda s: True)

    def fake_audio(video, directory, settings):
        calls.log.append(("audio", video.video_id))
        return directory + "/audio.m4a"

    def fake_transcribe(path, settings):
        calls.log.append(("whisper", path.rsplit("/", 1)[-1]))
        return "en", list(segments)

    monkeypatch.setattr(service_mod.ytdlp_source, "download_audio", fake_audio)
    monkeypatch.setattr(service_mod.speech, "transcribe", fake_transcribe)


def svc(**overrides):
    return TranscriptService(Settings(cache_ttl_seconds=0, **overrides))


def test_youtube_fast_path(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, result=([EN, AUTO_EN], EN, SEGMENTS))
    stub_ytdlp(monkeypatch, calls)
    result = svc().get_transcript(YT)
    assert calls.log == [("youtube_api", None)]
    assert (result.provider, result.kind, result.track_code) == ("youtube-transcript-api", "manual", "en")
    assert result.meta.title == "T"
    data = result.to_dict()
    assert data["text"] == "hello there general kenobi"
    assert data["paragraphs"] == [{"start": 0.0, "text": "hello there general kenobi"}]
    assert data["word_count"] == 4


def test_youtube_blocked_falls_back_to_ytdlp(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, error=UpstreamBlocked("YouTube is blocking."))
    stub_ytdlp(monkeypatch, calls, tracks=[AUTO_EN])
    result = svc().get_transcript(YT)
    assert calls.log == [("youtube_api", None), ("ytdlp_extract", YT.video_id), ("ytdlp_captions", "a.en")]
    assert result.provider == "yt-dlp"
    assert any("Used yt-dlp instead" in n for n in result.notes)


def test_both_routes_blocked_reports_both(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, error=UpstreamBlocked("first route blocked."))
    stub_ytdlp(monkeypatch, calls, error=UpstreamBlocked("second route blocked.", details=["yt-dlp said no"]))
    with pytest.raises(UpstreamBlocked) as info:
        svc().get_transcript(YT)
    assert any("first route blocked" in d for d in info.value.details)
    assert "yt-dlp said no" in info.value.details


def test_youtube_without_captions_stops_early(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, error=NoTranscriptAvailable("Captions are off."))
    stub_ytdlp(monkeypatch, calls)
    with pytest.raises(NoTranscriptAvailable):
        svc().get_transcript(YT)
    assert calls.log == [("youtube_api", None)]  # no pointless yt-dlp round trip


def test_youtube_without_captions_uses_speech_to_text_when_asked(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, error=NoTranscriptAvailable("Captions are off."))
    stub_ytdlp(monkeypatch, calls, tracks=[AUTO_EN])
    stub_speech(monkeypatch, calls)
    result = svc().get_transcript(YT, speech_to_text=True)
    assert ("ytdlp_captions", "a.en") not in calls.log  # captions were ruled out
    assert calls.log[-2:] == [("audio", YT.video_id), ("whisper", "audio.m4a")]
    assert (result.kind, result.language, result.provider) == ("speech-to-text", "en", "faster-whisper (base)")
    assert any("Whisper" in n for n in result.notes)


def test_captions_win_over_speech_to_text(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[AUTO_EN], platform="tiktok")
    stub_speech(monkeypatch, calls)
    result = svc().get_transcript(TT, speech_to_text=True)
    assert result.kind == "auto"
    assert not any(step == "whisper" for step, _ in calls.log)


def test_tiktok_without_captions(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok")
    with pytest.raises(NoTranscriptAvailable) as info:
        svc().get_transcript(TT)
    assert "speech-to-text" not in info.value.message  # not installed, so not offered
    assert any("PO token" in d for d in info.value.details)


def test_tiktok_without_captions_offers_speech_to_text_when_installed(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok")
    monkeypatch.setattr(service_mod.speech, "is_available", lambda s: True)
    with pytest.raises(NoTranscriptAvailable) as info:
        svc().get_transcript(TT)
    assert "speech-to-text" in info.value.message


def test_speech_to_text_not_installed(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok")
    with pytest.raises(SpeechToTextRefused):
        svc().get_transcript(TT, speech_to_text=True)


def test_speech_to_text_duration_cap(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok", duration=3600)
    stub_speech(monkeypatch, calls)
    with pytest.raises(SpeechToTextRefused) as info:
        svc(whisper_max_duration=600).get_transcript(TT, speech_to_text=True)
    assert "60 minutes" in info.value.message
    assert not any(step == "audio" for step, _ in calls.log)


def test_speech_to_text_busy(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok")
    stub_speech(monkeypatch, calls)
    with service_mod.speech.slot():
        with pytest.raises(SpeechToTextBusy):
            svc().get_transcript(TT, speech_to_text=True)


def test_silent_audio_is_not_a_transcript(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[], platform="tiktok")
    stub_speech(monkeypatch, calls, segments=[])
    with pytest.raises(NoTranscriptAvailable):
        svc().get_transcript(TT, speech_to_text=True)


def test_empty_caption_track_is_not_a_transcript(monkeypatch, calls):
    stub_ytdlp(monkeypatch, calls, tracks=[AUTO_EN], platform="tiktok", segments=[])
    with pytest.raises(NoTranscriptAvailable) as info:
        svc().get_transcript(TT)
    assert "The caption track was empty." in info.value.details


def test_successful_results_are_cached(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, result=([EN], EN, SEGMENTS))
    service = TranscriptService(Settings(cache_ttl_seconds=60))
    first = service.get_transcript(YT)
    second = service.get_transcript(YT)
    assert first is second
    assert calls.log == [("youtube_api", None)]
    service.get_transcript(YT, language="en")  # a different selection is a different entry
    assert len(calls.log) == 2


def test_errors_are_not_cached(monkeypatch, calls):
    stub_youtube_api(monkeypatch, calls, error=NoTranscriptAvailable("off"))
    service = TranscriptService(Settings(cache_ttl_seconds=60))
    for _ in range(2):
        with pytest.raises(NoTranscriptAvailable):
            service.get_transcript(YT)
    assert len(calls.log) == 2
