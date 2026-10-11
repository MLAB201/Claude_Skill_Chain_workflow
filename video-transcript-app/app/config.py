"""Runtime settings, read once from environment variables.

Every setting is optional; the defaults run the app locally with captions only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    # Caption language to pick when the request doesn't name one.
    preferred_languages: list[str] = field(default_factory=lambda: ["en"])
    # Optional outbound proxy (http://user:pass@host:port) for YouTube/TikTok
    # requests. Useful when a cloud host's IP gets bot-checked.
    proxy: str | None = None
    # Optional Netscape-format cookies file handed to yt-dlp.
    cookies_file: str | None = None
    # Network timeout for each upstream request, in seconds.
    socket_timeout: int = 20
    # Speech-to-text fallback (needs `pip install -r requirements-whisper.txt`).
    whisper_enabled: bool = True
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    # Longest video (seconds) we will download and run through Whisper.
    whisper_max_duration: int = 20 * 60
    # Largest audio file (bytes) we will download for Whisper.
    whisper_max_download_bytes: int = 200 * 1024 * 1024
    # Successful transcripts are cached in memory for this long.
    cache_ttl_seconds: int = 30 * 60
    cache_max_entries: int = 128


def load_settings() -> Settings:
    return Settings(
        preferred_languages=_list("TRANSCRIPT_LANGUAGES", ["en"]),
        proxy=os.environ.get("TRANSCRIPT_PROXY") or None,
        cookies_file=os.environ.get("YTDLP_COOKIES_FILE") or None,
        socket_timeout=_int("TRANSCRIPT_TIMEOUT", 20),
        whisper_enabled=_bool("WHISPER_ENABLED", True),
        whisper_model=os.environ.get("WHISPER_MODEL") or "base",
        whisper_device=os.environ.get("WHISPER_DEVICE") or "cpu",
        whisper_compute_type=os.environ.get("WHISPER_COMPUTE_TYPE") or "int8",
        whisper_max_duration=_int("WHISPER_MAX_DURATION", 20 * 60),
        whisper_max_download_bytes=_int("WHISPER_MAX_DOWNLOAD_MB", 200) * 1024 * 1024,
        cache_ttl_seconds=_int("TRANSCRIPT_CACHE_TTL", 30 * 60),
        cache_max_entries=_int("TRANSCRIPT_CACHE_SIZE", 128),
    )
