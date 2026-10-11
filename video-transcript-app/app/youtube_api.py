"""YouTube captions via youtube-transcript-api: the fast path (a few small
requests, no media download). When YouTube blocks it, the service falls back to
yt-dlp (see service.py).
"""

from __future__ import annotations

import logging
from typing import Optional

import requests
import youtube_transcript_api as yta
from youtube_transcript_api.proxies import GenericProxyConfig

from .config import Settings
from .models import (
    NoTranscriptAvailable,
    Segment,
    TrackInfo,
    UpstreamBlocked,
    UpstreamError,
    VideoMeta,
    VideoUnavailable,
)
from .captions import clean_text, finalize_segments
from .tracks import choose_track, track_code

log = logging.getLogger(__name__)

PROVIDER = "youtube-transcript-api"
OEMBED_URL = "https://www.youtube.com/oembed"


class TimeoutSession(requests.Session):
    """requests.Session with a default timeout (requests has none by default,
    so a stalled upstream would otherwise hang the worker forever)."""

    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return super().request(*args, **kwargs)


def fetch(
    video_id: str,
    requested: Optional[str],
    settings: Settings,
    http_client: Optional[requests.Session] = None,
) -> tuple[list[TrackInfo], TrackInfo, list[Segment]]:
    """Return (all tracks, chosen track, segments).

    Raises NoTranscriptAvailable / VideoUnavailable when YouTube gave a definite
    answer, and UpstreamBlocked / UpstreamError when it didn't (the caller should
    then try another route).
    """
    session = http_client or TimeoutSession(settings.socket_timeout)
    proxy = (
        GenericProxyConfig(http_url=settings.proxy, https_url=settings.proxy)
        if settings.proxy
        else None
    )
    api = yta.YouTubeTranscriptApi(proxy_config=proxy, http_client=session)

    try:
        listing = api.list(video_id)
        transcripts = {}
        tracks = []
        for transcript in listing:
            kind = "auto" if transcript.is_generated else "manual"
            code = track_code(transcript.language_code, kind)
            transcripts[code] = transcript
            tracks.append(
                TrackInfo(
                    code=code,
                    language=transcript.language_code,
                    name=transcript.language,
                    kind=kind,
                    # YouTube only auto-generates captions in the spoken language.
                    is_original=transcript.is_generated,
                )
            )
        chosen = choose_track(tracks, requested, settings.preferred_languages)
        fetched = transcripts[chosen.code].fetch()
    except (yta.TranscriptsDisabled, yta.NoTranscriptFound):
        raise NoTranscriptAvailable("Captions are turned off for this video.") from None
    except (yta.VideoUnavailable, yta.InvalidVideoId):
        raise VideoUnavailable("This YouTube video is unavailable (removed, private, or a bad ID).") from None
    except yta.RequestBlocked as exc:  # includes IpBlocked
        log.info("youtube-transcript-api blocked for %s: %s", video_id, type(exc).__name__)
        raise UpstreamBlocked(
            "YouTube is blocking caption requests from this server's IP address."
        ) from None
    except yta.YouTubeTranscriptApiException as exc:
        # PoTokenRequired, AgeRestricted, VideoUnplayable, request failures, ...
        raise UpstreamError(f"YouTube caption lookup failed ({type(exc).__name__}).") from None
    except requests.RequestException as exc:
        raise UpstreamError(f"Couldn't reach YouTube ({type(exc).__name__}).") from None

    segments = finalize_segments(
        Segment(s.start, s.start + s.duration, clean_text(s.text)) for s in fetched
    )
    return tracks, chosen, segments


def fetch_metadata(video_id: str, settings: Settings, http_client: Optional[requests.Session] = None) -> VideoMeta:
    """Best-effort title/author via YouTube's public oEmbed endpoint. Never raises."""
    meta = VideoMeta(thumbnail=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
    session = http_client or TimeoutSession(min(settings.socket_timeout, 8))
    if settings.proxy and http_client is None:
        session.proxies = {"http": settings.proxy, "https": settings.proxy}
    try:
        resp = session.get(
            OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
        )
        if resp.ok:
            data = resp.json()
            meta.title = data.get("title") or None
            meta.author = data.get("author_name") or None
    except (requests.RequestException, ValueError):
        pass
    return meta
