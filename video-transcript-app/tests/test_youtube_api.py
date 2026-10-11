"""Drives the real youtube-transcript-api library offline, through a fake HTTP
adapter that replays recorded YouTube responses (see fixtures/README.md)."""

import pytest
import requests

from app import youtube_api
from app.models import NoTranscriptAvailable, UpstreamBlocked, UpstreamError, VideoUnavailable

from conftest import FakeYouTube, fake_youtube_session

VIDEO = "GJLlxj_dtq8"


def run(adapter, settings, requested=None):
    return youtube_api.fetch(VIDEO, requested, settings, http_client=fake_youtube_session(adapter))


def test_lists_tracks_and_picks_manual_english(settings):
    adapter = FakeYouTube()
    tracks, chosen, segments = run(adapter, settings)

    assert [(t.code, t.kind, t.is_original) for t in tracks] == [
        ("en", "manual", False),
        ("de", "manual", False),
        ("a.en", "auto", True),
    ]
    assert chosen.code == "en"
    assert adapter.timedtext_langs() == [("en", None)]  # fetched the manual track
    assert [(s.text, s.start, s.end) for s in segments] == [
        ("Hey, this is just a test", 0.0, 1.54),
        ("this is not the original transcript", 1.54, 5.7),
        ("just something shorter, I made up for testing", 5.7, 8.939),
    ]


@pytest.mark.parametrize("requested, expected", [("de", ("de", None)), ("a.en", ("en", "asr"))])
def test_requested_track_is_the_one_fetched(settings, requested, expected):
    adapter = FakeYouTube()
    _, chosen, _ = run(adapter, settings, requested)
    assert chosen.code == requested
    assert adapter.timedtext_langs() == [expected]


def test_bot_check_maps_to_blocked(settings):
    with pytest.raises(UpstreamBlocked):
        run(FakeYouTube(innertube="youtube_innertube_blocked.json"), settings)


def test_no_captions(settings):
    with pytest.raises(NoTranscriptAvailable):
        run(FakeYouTube(innertube="youtube_innertube_no_captions.json"), settings)


def test_unavailable_video(settings):
    with pytest.raises(VideoUnavailable):
        run(FakeYouTube(innertube="youtube_innertube_unavailable.json"), settings)


def test_network_failure_is_an_upstream_error(settings):
    with pytest.raises(UpstreamError):
        run(FakeYouTube(fail=requests.ConnectionError("boom")), settings)


def test_metadata_from_oembed(settings):
    adapter = FakeYouTube(oembed={"title": "Surface Go Review", "author_name": "Unbox Therapy"})
    meta = youtube_api.fetch_metadata(VIDEO, settings, http_client=fake_youtube_session(adapter))
    assert (meta.title, meta.author) == ("Surface Go Review", "Unbox Therapy")
    assert meta.thumbnail == f"https://i.ytimg.com/vi/{VIDEO}/hqdefault.jpg"


def test_metadata_failure_is_harmless(settings):
    meta = youtube_api.fetch_metadata(VIDEO, settings, http_client=fake_youtube_session(FakeYouTube()))
    assert meta.title is None and meta.thumbnail
    broken = FakeYouTube(fail=requests.Timeout("slow"))
    meta = youtube_api.fetch_metadata(VIDEO, settings, http_client=fake_youtube_session(broken))
    assert meta.title is None
