"""Captions (and, for speech-to-text, audio) via yt-dlp. Handles both YouTube and
TikTok, so it is the only route for TikTok and the fallback route for YouTube.

Security posture: yt-dlp is restricted to the YouTube and TikTok extractors
(`allowed_extractors`), so even a redirect can't make it fetch an arbitrary
site through the generic extractor. Downloads go to a private temporary
directory that is deleted afterwards, and caption/audio sizes are capped.
"""

from __future__ import annotations

import copy
import glob
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import yt_dlp
from yt_dlp.utils import DownloadError

from .captions import parse_caption_file
from .config import Settings
from .models import (
    InvalidVideoUrl,
    NoTranscriptAvailable,
    Segment,
    SpeechToTextRefused,
    TrackInfo,
    UpstreamBlocked,
    UpstreamError,
    VideoMeta,
    VideoUnavailable,
)
from .tracks import track_code
from .urls import VideoRef, parse_video_url

log = logging.getLogger(__name__)

PROVIDER = "yt-dlp"
ALLOWED_EXTRACTORS = [r"youtube", r"tiktok", r"vm\.tiktok"]
# Caption formats we can parse, best first. Anything else is never requested.
CAPTION_FORMATS = ("json3", "vtt", "srt")
MAX_CAPTION_BYTES = 8 * 1024 * 1024

# Substrings of yt-dlp error messages, mapped to what they mean for the user.
_BLOCKED_HINTS = (
    "confirm you're not a bot",
    "confirm you’re not a bot",
    "http error 429",
    "too many requests",
    "ip address is blocked",
    "your ip address",
)
_UNAVAILABLE_HINTS = (
    "video unavailable",
    "this video is unavailable",
    "private video",
    "has been removed",
    "this video has been removed",
    "video is not available",
    "not available in your country",
    "post is unavailable",
    "http error 404",
)
# yt-dlp warnings worth passing on when no captions turn up.
_RELEVANT_WARNING_RE = re.compile(r"subtitle|caption|po token|javascript runtime|sign in", re.I)


class _CollectingLogger:
    def __init__(self):
        self.warnings: list[str] = []
        self.file_too_large = False

    def debug(self, msg):
        # yt-dlp reports a max_filesize abort as a screen message, not a warning.
        if "max-filesize" in str(msg):
            self.file_too_large = True

    def info(self, msg):
        pass

    def warning(self, msg):
        self.warnings.append(str(msg))

    def error(self, msg):
        log.debug("yt-dlp error: %s", msg)


@dataclass
class VideoInfo:
    platform: str
    video_id: str
    url: str
    meta: VideoMeta
    tracks: list[TrackInfo]
    raw: dict  # yt-dlp's info dict, reused for the caption/audio download step
    # track code -> (yt-dlp subtitle key, True if it lives in automatic_captions)
    caption_keys: dict[str, tuple[str, bool]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def relevant_warnings(self) -> list[str]:
        out = []
        for w in self.warnings:
            if _RELEVANT_WARNING_RE.search(w):
                out.append(_clean_message(w))
        return out[:3]


def _base_opts(settings: Settings, logger: _CollectingLogger) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": False,
        "noprogress": True,
        "logger": logger,
        "skip_download": True,
        "noplaylist": True,
        "allowed_extractors": ALLOWED_EXTRACTORS,
        "socket_timeout": settings.socket_timeout,
        "retries": 2,
        "extractor_retries": 1,
        "cachedir": False,
        # Formats only matter for speech-to-text; don't fail when YouTube hides
        # them (e.g. no JavaScript runtime installed for yt-dlp).
        "ignore_no_formats_error": True,
        "format": "bestaudio/worst[acodec!=none]/best",
    }
    if settings.proxy:
        opts["proxy"] = settings.proxy
    if settings.cookies_file:
        opts["cookiefile"] = settings.cookies_file
    return opts


def _clean_message(msg: str) -> str:
    msg = re.sub(r"^(ERROR|WARNING):\s*", "", str(msg).strip())
    msg = re.sub(r"^\[[\w.:-]+\]\s*[\w-]*:\s*", "", msg)  # "[youtube] abc123: ..."
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)  # ANSI colour codes
    msg = re.sub(r";?\s*please report this issue on .*$", "", msg, flags=re.I | re.S)  # yt-dlp boilerplate
    return msg[:300]


def _map_error(exc: Exception, platform: str, *, lookup: bool = True) -> Exception:
    """Translate a yt-dlp error. `lookup` is False for caption/audio downloads,
    where e.g. a 404 means the file failed, not that the video is gone."""
    message = _clean_message(str(exc))
    lower = message.lower()
    site = "YouTube" if platform == "youtube" else "TikTok"
    if any(h in lower for h in _BLOCKED_HINTS):
        return UpstreamBlocked(
            f"{site} is blocking requests from this server's IP address.", details=[message]
        )
    if lookup and any(h in lower for h in _UNAVAILABLE_HINTS):
        return VideoUnavailable(f"This {site} video is unavailable.", details=[message])
    if not lookup:
        return UpstreamError(f"Couldn't download this video's data from {site}.", details=[message])
    return UpstreamError(f"Couldn't read this video from {site}.", details=[message])


def extract(ref: VideoRef, settings: Settings) -> VideoInfo:
    """Fetch video metadata and the list of caption tracks (no downloads)."""
    logger = _CollectingLogger()
    try:
        with yt_dlp.YoutubeDL(_base_opts(settings, logger)) as ydl:
            info = ydl.extract_info(ref.url, download=False)
    except DownloadError as exc:
        raise _map_error(exc, ref.platform) from None

    if not isinstance(info, dict) or info.get("_type", "video") != "video":
        raise InvalidVideoUrl("That link doesn't point to a single video.")

    tracks, keys = _collect_tracks(info, ref.platform)
    video_id = str(info.get("id") or ref.video_id)
    # The page URL ends up as a link in the UI, so only trust it if it is itself
    # a valid link for the same platform.
    try:
        resolved = parse_video_url(str(info.get("webpage_url") or ""))
        url = resolved.url if resolved.platform == ref.platform else ref.url
    except InvalidVideoUrl:
        url = ref.url
    meta = VideoMeta(
        title=info.get("title") or None,
        author=info.get("channel") or info.get("uploader") or info.get("creator") or None,
        duration=float(info["duration"]) if isinstance(info.get("duration"), (int, float)) else None,
        thumbnail=info.get("thumbnail") or None,
    )
    return VideoInfo(
        platform=ref.platform,
        video_id=video_id,
        url=url,
        meta=meta,
        tracks=tracks,
        raw=info,
        caption_keys=keys,
        warnings=logger.warnings,
    )


def _entries(value) -> list[dict]:
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def _has_parseable_format(entries: list[dict]) -> bool:
    return any(e.get("ext") in CAPTION_FORMATS for e in entries)


def _collect_tracks(info: dict, platform: str) -> tuple[list[TrackInfo], dict[str, tuple[str, bool]]]:
    tracks: list[TrackInfo] = []
    keys: dict[str, tuple[str, bool]] = {}

    def add(lang_key: str, language: str, name: str, kind: str, from_auto: bool, is_original: bool):
        code = track_code(language, kind)
        if code in keys:
            return
        keys[code] = (lang_key, from_auto)
        tracks.append(TrackInfo(code=code, language=language, name=name, kind=kind, is_original=is_original))

    subtitles = {k: _entries(v) for k, v in (info.get("subtitles") or {}).items()}
    automatic = {k: _entries(v) for k, v in (info.get("automatic_captions") or {}).items()}

    if platform == "tiktok":
        # TikTok's captions are generated by TikTok (creators can edit them), and
        # yt-dlp lists them all under `subtitles` without marking the original.
        for lang_key, entries in subtitles.items():
            if lang_key == "live_chat" or not _has_parseable_format(entries):
                continue
            add(lang_key, lang_key, f"{lang_key} (TikTok captions)", "auto", False, False)
        return tracks, keys

    for lang_key, entries in subtitles.items():
        if lang_key == "live_chat" or not _has_parseable_format(entries):
            continue
        name = next((e.get("name") for e in entries if e.get("name")), None) or lang_key
        add(lang_key, lang_key, name, "manual", False, False)

    # YouTube lists ~100 machine translations under automatic_captions; their URLs
    # carry `tlang=`. Keep only the untranslated track (in the spoken language),
    # which yt-dlp also labels "<lang>-orig".
    originals = [
        (lang_key, entries)
        for lang_key, entries in automatic.items()
        if _has_parseable_format(entries)
        and not any("tlang=" in str(e.get("url", "")) for e in entries)
    ]
    originals.sort(key=lambda item: not item[0].endswith("-orig"))  # "-orig" first
    for lang_key, entries in originals:
        language = lang_key.removesuffix("-orig")
        name = next((e.get("name") for e in entries if e.get("name")), None) or language
        name = name.replace(" (Original)", "")
        add(lang_key, language, f"{name} (auto-generated)", "auto", True, True)
    return tracks, keys


def _prepared_info(video: VideoInfo) -> dict:
    """A clean copy of the info dict for a second processing pass (the same thing
    yt-dlp's own --load-info-json does)."""
    info = yt_dlp.YoutubeDL.sanitize_info(copy.deepcopy(video.raw), remove_private_keys=True)
    info["subtitles"] = {}
    info["automatic_captions"] = {}
    return info


def download_captions(video: VideoInfo, track: TrackInfo, settings: Settings) -> list[Segment]:
    lang_key, from_auto = video.caption_keys[track.code]
    entries = _entries((video.raw.get("automatic_captions" if from_auto else "subtitles") or {}).get(lang_key))
    usable = [e for e in entries if e.get("ext") in CAPTION_FORMATS]
    if not usable:
        raise NoTranscriptAvailable("This video's captions are in a format we can't read.")

    # Inline caption data (TikTok sometimes embeds it): no download needed.
    for ext in CAPTION_FORMATS:
        for entry in usable:
            if entry["ext"] == ext and isinstance(entry.get("data"), str):
                return parse_caption_file(entry["data"], ext)

    info = _prepared_info(video)
    info["automatic_captions" if from_auto else "subtitles"] = {lang_key: copy.deepcopy(usable)}
    logger = _CollectingLogger()
    with tempfile.TemporaryDirectory(prefix="transcript-captions-") as tmp:
        opts = {
            **_base_opts(settings, logger),
            "writesubtitles": not from_auto,
            "writeautomaticsub": from_auto,
            "subtitleslangs": [re.escape(lang_key)],
            "subtitlesformat": "/".join(CAPTION_FORMATS),
            "outtmpl": {"default": os.path.join(tmp, "captions.%(ext)s")},
            "paths": {"home": tmp, "temp": tmp},
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                processed = ydl.process_ie_result(info, download=True)
        except DownloadError as exc:
            raise _map_error(exc, video.platform, lookup=False) from None

        sub = ((processed or {}).get("requested_subtitles") or {}).get(lang_key) or {}
        path = sub.get("filepath")
        ext = sub.get("ext")
        if not path or not os.path.exists(path):
            found = sorted(glob.glob(os.path.join(tmp, "captions.*")))
            path = found[0] if found else None
            ext = path.rsplit(".", 1)[-1] if path else None
        if not path:
            video.warnings.extend(logger.warnings)
            raise UpstreamError(
                "The caption file couldn't be downloaded.",
                details=[_clean_message(w) for w in logger.warnings[-3:]],
            )
        if os.path.getsize(path) > MAX_CAPTION_BYTES:
            raise UpstreamError("The caption file is unreasonably large; refusing to parse it.")
        with open(path, encoding="utf-8", errors="replace") as fh:
            return parse_caption_file(fh.read(), ext or "")


def download_audio(video: VideoInfo, directory: str, settings: Settings) -> str:
    """Download the smallest audio-bearing stream into `directory` and return its path."""
    info = _prepared_info(video)
    logger = _CollectingLogger()
    opts = {
        **_base_opts(settings, logger),
        "skip_download": False,
        "max_filesize": settings.whisper_max_download_bytes,
        "outtmpl": {"default": os.path.join(directory, "audio.%(ext)s")},
        "paths": {"home": directory, "temp": directory},
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            processed = ydl.process_ie_result(info, download=True)
    except DownloadError as exc:
        raise _map_error(exc, video.platform, lookup=False) from None

    path: Optional[str] = None
    for item in (processed or {}).get("requested_downloads") or []:
        if item.get("filepath") and os.path.exists(item["filepath"]):
            path = item["filepath"]
    if not path:
        found = [p for p in glob.glob(os.path.join(directory, "audio.*")) if not p.endswith(".part")]
        path = found[0] if found else None
    if not path:
        if logger.file_too_large:
            raise SpeechToTextRefused(
                f"The audio is larger than the {settings.whisper_max_download_bytes // (1024 * 1024)} MB "
                "speech-to-text limit."
            )
        raise UpstreamError(
            "Couldn't download this video's audio for speech-to-text.",
            details=[_clean_message(w) for w in logger.warnings[-3:]],
        )
    return path
