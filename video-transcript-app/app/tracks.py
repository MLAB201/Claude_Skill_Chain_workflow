"""Choosing which caption track to return.

Policy when the caller doesn't name a language:
  1. a creator-made (manual) track in a preferred language
  2. an auto-generated track in a preferred language
  3. a manual track in the video's spoken language
  4. the auto-generated track in the spoken language
  5. any manual track, then any auto track

Machine-translated tracks are never offered: they are a different (and much
less faithful) thing than a transcript of what was said.
"""

from __future__ import annotations

from typing import Optional

from .models import NoTranscriptAvailable, TrackInfo

# Track codes: a manual track's code is its language ("en"); an auto-generated
# track's is "a.<language>" ("a.en"), mirroring YouTube's own vssId convention, so
# a video's manual and auto tracks in the same language stay distinguishable.
AUTO_PREFIX = "a."


def track_code(language: str, kind: str) -> str:
    return language if kind == "manual" else AUTO_PREFIX + language


# TikTok labels tracks with ISO 639-2 codes ("eng-US"); YouTube uses 639-1 ("en").
_ISO639_2_TO_1 = {
    "ara": "ar", "chi": "zh", "zho": "zh", "cmn": "zh", "deu": "de", "ger": "de",
    "dut": "nl", "nld": "nl", "eng": "en", "fil": "tl", "fra": "fr", "fre": "fr",
    "heb": "he", "hin": "hi", "ind": "id", "ita": "it", "jpn": "ja", "kor": "ko",
    "may": "ms", "msa": "ms", "pol": "pl", "por": "pt", "rus": "ru", "spa": "es",
    "swe": "sv", "tha": "th", "tur": "tr", "ukr": "uk", "vie": "vi",
}


def base_language(code: str) -> str:
    """'en-US' -> 'en', 'eng-US' -> 'en', 'zh-Hans' -> 'zh', 'en-orig' -> 'en'."""
    head = code.replace("_", "-").split("-", 1)[0].lower()
    return _ISO639_2_TO_1.get(head, head)


def choose_track(
    tracks: list[TrackInfo],
    requested: Optional[str],
    preferred: list[str],
) -> TrackInfo:
    if not tracks:
        raise NoTranscriptAvailable("This video has no captions.")

    manual = [t for t in tracks if t.kind == "manual"]
    auto = [t for t in tracks if t.kind == "auto"]

    if requested:
        for track in tracks:
            if track.code == requested:
                return track
        wanted = base_language(requested.removeprefix(AUTO_PREFIX))
        for pool in (manual, auto):
            for track in pool:
                if base_language(track.language) == wanted:
                    return track
        raise NoTranscriptAvailable(
            f"No captions in '{requested}' for this video.",
            details=["Available: " + ", ".join(f"{t.name} [{t.code}]" for t in tracks)],
        )

    for lang in preferred:
        wanted = base_language(lang)
        for pool in (manual, auto):
            for track in pool:
                if base_language(track.language) == wanted:
                    return track

    original = next((t for t in auto if t.is_original), None)
    if original:
        spoken = base_language(original.language)
        for track in manual:
            if base_language(track.language) == spoken:
                return track
        return original

    return (manual or auto)[0]
