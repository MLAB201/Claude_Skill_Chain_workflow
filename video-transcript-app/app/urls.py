"""Parse and validate user-supplied video URLs.

Security posture: only YouTube and TikTok hosts are accepted, matched exactly
(no suffix matching, so `youtube.com.evil.test` is rejected). The URL handed to
the extractors is rebuilt from the parsed ID, never the raw user string, so a
crafted URL can't steer yt-dlp at another host. yt-dlp is additionally limited
to the YouTube/TikTok extractors (see ytdlp_source.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from .models import InvalidVideoUrl

MAX_URL_LENGTH = 2048

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
TIKTOK_ID_RE = re.compile(r"^\d{8,25}$")
TIKTOK_SHORT_CODE_RE = re.compile(r"^[A-Za-z0-9]{4,32}$")
TIKTOK_USER_RE = re.compile(r"^[\w.-]{1,64}$")

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
YOUTUBE_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
TIKTOK_HOSTS = {"tiktok.com", "www.tiktok.com", "m.tiktok.com"}
TIKTOK_SHORT_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}

# Path prefixes that are followed directly by a YouTube video ID.
_YOUTUBE_ID_PATHS = ("shorts", "live", "embed", "v", "e")


@dataclass(frozen=True)
class VideoRef:
    platform: str  # "youtube" | "tiktok"
    video_id: str  # YouTube ID, TikTok numeric ID, or TikTok short-link code
    url: str  # canonical URL, safe to hand to the extractors
    is_short_link: bool = False  # TikTok vm./vt. link: real ID is resolved later


def parse_video_url(raw: str) -> VideoRef:
    text = (raw or "").strip()
    if not text:
        raise InvalidVideoUrl("Paste a YouTube or TikTok video link.")
    if len(text) > MAX_URL_LENGTH:
        raise InvalidVideoUrl("That link is too long to be a video URL.")

    # A bare 11-character YouTube ID is accepted as a convenience.
    if YOUTUBE_ID_RE.match(text):
        return _youtube(text)

    if "://" not in text:
        text = "https://" + text

    try:
        parts = urlsplit(text)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        raise InvalidVideoUrl("That doesn't look like a valid link.") from None

    if parts.scheme.lower() not in {"http", "https"}:
        raise InvalidVideoUrl("Only http(s) links are supported.")

    segments = [s for s in parts.path.split("/") if s]

    if host in YOUTUBE_HOSTS:
        return _parse_youtube(segments, parts.query)
    if host in YOUTUBE_SHORT_HOSTS:
        if segments and YOUTUBE_ID_RE.match(segments[0]):
            return _youtube(segments[0])
        raise InvalidVideoUrl("That youtu.be link is missing a video ID.")
    if host in TIKTOK_HOSTS:
        return _parse_tiktok(segments)
    if host in TIKTOK_SHORT_HOSTS:
        if segments and TIKTOK_SHORT_CODE_RE.match(segments[0]):
            code = segments[0]
            return VideoRef("tiktok", code, f"https://{host}/{code}/", is_short_link=True)
        raise InvalidVideoUrl("That TikTok short link is missing its code.")

    raise InvalidVideoUrl(
        "Only YouTube and TikTok links are supported.",
        details=[f"Got a link to '{host or 'an unknown host'}'."],
    )


def _youtube(video_id: str) -> VideoRef:
    return VideoRef("youtube", video_id, f"https://www.youtube.com/watch?v={video_id}")


def _parse_youtube(segments: list[str], query: str) -> VideoRef:
    if segments[:1] == ["watch"] or not segments:
        candidate = (parse_qs(query).get("v") or [""])[0]
        if YOUTUBE_ID_RE.match(candidate):
            return _youtube(candidate)
        if "list" in parse_qs(query):
            raise InvalidVideoUrl("Playlists aren't supported — open one video and paste its link.")
        raise InvalidVideoUrl("That YouTube link is missing a video ID (the ?v=… part).")
    if len(segments) >= 2 and segments[0] in _YOUTUBE_ID_PATHS:
        if YOUTUBE_ID_RE.match(segments[1]):
            return _youtube(segments[1])
    if segments[0] in {"playlist", "channel", "c", "user"} or segments[0].startswith("@"):
        raise InvalidVideoUrl("That's a channel or playlist link — paste a link to a single video.")
    raise InvalidVideoUrl("That YouTube link doesn't point to a video.")


def _parse_tiktok(segments: list[str]) -> VideoRef:
    # /@user/video/123, /@user/photo/123
    if len(segments) >= 3 and segments[0].startswith("@") and segments[1] in {"video", "photo"}:
        user = segments[0][1:]
        video_id = segments[2]
        if segments[1] == "photo":
            raise InvalidVideoUrl("TikTok photo posts have no video to transcribe.")
        if TIKTOK_ID_RE.match(video_id):
            user = user if TIKTOK_USER_RE.match(user) else "_"
            return VideoRef("tiktok", video_id, f"https://www.tiktok.com/@{user}/video/{video_id}")
    # /embed/123, /embed/v2/123, /share/video/123, /v/123.html (old mobile links)
    if segments and segments[0] in {"embed", "share", "v"}:
        candidate = segments[-1].removesuffix(".html")
        if TIKTOK_ID_RE.match(candidate):
            return VideoRef("tiktok", candidate, f"https://www.tiktok.com/@_/video/{candidate}")
    # /t/CODE short links on the main domain
    if len(segments) >= 2 and segments[0] == "t" and TIKTOK_SHORT_CODE_RE.match(segments[1]):
        code = segments[1]
        return VideoRef("tiktok", code, f"https://www.tiktok.com/t/{code}/", is_short_link=True)
    raise InvalidVideoUrl("That TikTok link doesn't point to a video.")
