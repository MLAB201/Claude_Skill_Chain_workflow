"""The transcript pipeline: pick a route per platform, fall back when a route is
blocked, and say exactly where the text came from.

  YouTube:  youtube-transcript-api  ->  yt-dlp captions  ->  [speech-to-text]
  TikTok:   yt-dlp captions                              ->  [speech-to-text]

Speech-to-text only runs when the caller opts in AND the video has no usable
captions. A result is never padded or guessed: if no route produces text, the
caller gets a NoTranscriptAvailable error listing what was tried.
"""

from __future__ import annotations

import logging
import tempfile
import threading
import time
from collections import OrderedDict
from typing import Optional

from . import speech, youtube_api, ytdlp_source
from .config import Settings
from .models import (
    NoTranscriptAvailable,
    SpeechToTextRefused,
    TranscriptResult,
    UpstreamBlocked,
    UpstreamError,
    VideoMeta,
)
from .tracks import choose_track
from .urls import VideoRef

log = logging.getLogger(__name__)


class _TTLCache:
    def __init__(self, ttl: int, max_entries: int):
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.monotonic():
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def put(self, key, value):
        if self.ttl <= 0 or self.max_entries <= 0:
            return
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)


class TranscriptService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache = _TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)

    def speech_to_text_available(self) -> bool:
        return speech.is_available(self.settings)

    def get_transcript(
        self, ref: VideoRef, language: Optional[str] = None, speech_to_text: bool = False
    ) -> TranscriptResult:
        # Errors are never cached; a cached success is valid whatever the
        # speech_to_text flag, because captions always win over speech-to-text.
        key = (ref.platform, ref.video_id, language or "")
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._resolve(ref, language, speech_to_text)
        self._cache.put(key, result)
        return result

    def _resolve(self, ref: VideoRef, language: Optional[str], speech_to_text: bool) -> TranscriptResult:
        notes: list[str] = []
        captions_ruled_out = False

        if ref.platform == "youtube":
            try:
                tracks, chosen, segments = youtube_api.fetch(ref.video_id, language, self.settings)
            except NoTranscriptAvailable as exc:
                if not speech_to_text:
                    raise
                notes.append(exc.message)
                captions_ruled_out = True
            except (UpstreamBlocked, UpstreamError) as exc:
                log.info("youtube-transcript-api failed for %s, trying yt-dlp: %s", ref.video_id, exc.message)
                notes.append(f"{exc.message} Used yt-dlp instead.")
            else:
                if segments:
                    return TranscriptResult(
                        platform="youtube",
                        video_id=ref.video_id,
                        url=ref.url,
                        track_code=chosen.code,
                        language=chosen.language,
                        language_name=chosen.name,
                        kind=chosen.kind,
                        provider=youtube_api.PROVIDER,
                        segments=segments,
                        tracks=tracks,
                        meta=youtube_api.fetch_metadata(ref.video_id, self.settings),
                    )
                notes.append("YouTube returned an empty caption track. Used yt-dlp instead.")

        try:
            video = ytdlp_source.extract(ref, self.settings)
        except (UpstreamBlocked, UpstreamError) as exc:
            exc.details = notes + exc.details
            raise

        if not captions_ruled_out and video.tracks:
            try:
                chosen = choose_track(video.tracks, language, self.settings.preferred_languages)
            except NoTranscriptAvailable as exc:
                if not speech_to_text:
                    raise
                notes.append(exc.message)
            else:
                segments = ytdlp_source.download_captions(video, chosen, self.settings)
                if segments:
                    return TranscriptResult(
                        platform=video.platform,
                        video_id=video.video_id,
                        url=video.url,
                        track_code=chosen.code,
                        language=chosen.language,
                        language_name=chosen.name,
                        kind=chosen.kind,
                        provider=ytdlp_source.PROVIDER,
                        segments=segments,
                        tracks=video.tracks,
                        meta=self._meta_with_fallback(video.meta, ref),
                        notes=notes,
                    )
                notes.append("The caption track was empty.")
        elif not captions_ruled_out:
            notes.append("No captions were found for this video.")
            notes.extend(video.relevant_warnings())

        if speech_to_text:
            return self._speech_to_text(video, notes)

        hint = (
            " Turn on speech-to-text to transcribe the audio instead."
            if self.speech_to_text_available()
            else ""
        )
        raise NoTranscriptAvailable("This video has no captions." + hint, details=notes)

    def _speech_to_text(self, video: ytdlp_source.VideoInfo, notes: list[str]) -> TranscriptResult:
        settings = self.settings
        if not speech.is_available(settings):
            raise SpeechToTextRefused(
                "This video has no captions, and speech-to-text isn't installed on this server.",
                details=notes + ["Install it with: pip install -r requirements-whisper.txt"],
            )
        duration = video.meta.duration
        if duration is not None and duration > settings.whisper_max_duration:
            raise SpeechToTextRefused(
                f"This video is {duration / 60:.0f} minutes long; speech-to-text is limited "
                f"to {settings.whisper_max_duration / 60:.0f} minutes.",
                details=notes,
            )

        with speech.slot():
            with tempfile.TemporaryDirectory(prefix="transcript-audio-") as tmp:
                audio_path = ytdlp_source.download_audio(video, tmp, settings)
                detected, segments = speech.transcribe(audio_path, settings)

        if not segments:
            raise NoTranscriptAvailable("No speech was detected in this video's audio.", details=notes)

        notes.append(
            "No captions were available, so this was transcribed from the audio with "
            f"Whisper ({settings.whisper_model}). Expect some mistakes, especially with names."
        )
        return TranscriptResult(
            platform=video.platform,
            video_id=video.video_id,
            url=video.url,
            track_code="speech-to-text",
            language=detected,
            language_name=detected,
            kind="speech-to-text",
            provider=f"faster-whisper ({settings.whisper_model})",
            segments=segments,
            tracks=video.tracks,
            meta=video.meta,
            notes=notes,
        )

    @staticmethod
    def _meta_with_fallback(meta: VideoMeta, ref: VideoRef) -> VideoMeta:
        if ref.platform == "youtube" and not meta.thumbnail:
            meta.thumbnail = f"https://i.ytimg.com/vi/{ref.video_id}/hqdefault.jpg"
        return meta
