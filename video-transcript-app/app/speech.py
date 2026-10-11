"""Optional local speech-to-text with faster-whisper, used only when a video has
no captions and the caller asked for it.

faster-whisper is an optional dependency (requirements-whisper.txt). The model is
downloaded from Hugging Face on first use and then cached. Only one transcription
runs at a time: it's CPU-heavy, and a queue of them would just time out.
"""

from __future__ import annotations

import contextlib
import importlib.util
import threading

from .captions import clean_text, finalize_segments
from .config import Settings
from .models import Segment, SpeechToTextBusy

_model = None
_model_name = None
_model_lock = threading.Lock()
_busy = threading.Lock()


def is_installed() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def is_available(settings: Settings) -> bool:
    return settings.whisper_enabled and is_installed()


@contextlib.contextmanager
def slot():
    """Hold the single speech-to-text slot, or fail fast if it's taken."""
    if not _busy.acquire(blocking=False):
        raise SpeechToTextBusy(
            "Speech-to-text is already running for another video. Try again in a minute."
        )
    try:
        yield
    finally:
        _busy.release()


def _get_model(settings: Settings):
    global _model, _model_name
    with _model_lock:
        if _model is None or _model_name != settings.whisper_model:
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            _model_name = settings.whisper_model
        return _model


def transcribe(audio_path: str, settings: Settings) -> tuple[str, list[Segment]]:
    """Return (detected language code, segments)."""
    model = _get_model(settings)
    # vad_filter skips long silences/music, which is where Whisper tends to
    # hallucinate text that was never spoken.
    segments, info = model.transcribe(audio_path, vad_filter=True)
    out = [Segment(s.start, s.end, clean_text(s.text)) for s in segments]
    return info.language, finalize_segments(out)
