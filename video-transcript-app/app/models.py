"""Data shapes shared by every transcript source, plus the error types the API maps
to HTTP responses.

Every source (youtube-transcript-api, yt-dlp, local Whisper) produces the same
`TranscriptResult`, so the API layer and the frontend only ever see one shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

TrackKind = Literal["manual", "auto", "speech-to-text"]


@dataclass
class Segment:
    start: float  # seconds
    end: float  # seconds
    text: str


@dataclass
class TrackInfo:
    """One caption track the platform offers for a video."""

    code: str  # unique key; send it back as `language` to select this track
    language: str  # language code as the platform reports it, e.g. "en", "eng-US"
    name: str  # human-readable label, e.g. "English (auto-generated)"
    kind: TrackKind
    is_original: bool = False  # True for the auto track in the spoken language


@dataclass
class VideoMeta:
    title: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[float] = None  # seconds
    thumbnail: Optional[str] = None


@dataclass
class TranscriptResult:
    platform: str
    video_id: str
    url: str
    track_code: str
    language: str
    language_name: str
    kind: TrackKind
    provider: str  # which backend produced the text
    segments: list[Segment]
    tracks: list[TrackInfo] = field(default_factory=list)
    meta: VideoMeta = field(default_factory=VideoMeta)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        from .captions import segments_to_paragraphs

        paragraphs = segments_to_paragraphs(self.segments)
        text = "\n\n".join(p for _, p in paragraphs)
        return {
            "platform": self.platform,
            "video_id": self.video_id,
            "url": self.url,
            "title": self.meta.title,
            "author": self.meta.author,
            "duration": self.meta.duration,
            "thumbnail": self.meta.thumbnail,
            "track_code": self.track_code,
            "language": self.language,
            "language_name": self.language_name,
            "kind": self.kind,
            "provider": self.provider,
            "tracks": [asdict(t) for t in self.tracks],
            "segments": [asdict(s) for s in self.segments],
            "paragraphs": [{"start": start, "text": p} for start, p in paragraphs],
            "text": text,
            "word_count": len(text.split()),
            "notes": self.notes,
        }


class TranscriptError(Exception):
    """Base error. `code` is stable and machine-readable; `message` is shown to users."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: Optional[list[str]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class InvalidVideoUrl(TranscriptError):
    status_code = 400
    code = "invalid_url"


class VideoUnavailable(TranscriptError):
    status_code = 404
    code = "video_unavailable"


class NoTranscriptAvailable(TranscriptError):
    status_code = 404
    code = "no_transcript"


class UpstreamBlocked(TranscriptError):
    """The platform refused this server (bot check, IP block, rate limit)."""

    status_code = 503
    code = "upstream_blocked"


class UpstreamError(TranscriptError):
    status_code = 502
    code = "upstream_error"


class SpeechToTextBusy(TranscriptError):
    status_code = 429
    code = "speech_to_text_busy"


class SpeechToTextRefused(TranscriptError):
    """Speech-to-text was asked for but can't run (not installed, video too long)."""

    status_code = 422
    code = "speech_to_text_unavailable"
