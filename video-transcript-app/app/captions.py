"""Caption file parsers (WebVTT, SRT, YouTube json3) and transcript text helpers.

All parsers are pure functions that take the caption file as text and return a
cleaned, time-ordered list of `Segment`s. They never raise on malformed input:
unparseable blocks are skipped, and an empty list tells the caller the file held
no usable text (the caller then reports that instead of returning a blank
transcript).
"""

from __future__ import annotations

import html
import json
import re

from .models import Segment

# Hard caps so a hostile or broken caption file can't exhaust memory/CPU.
MAX_CAPTION_CHARS = 8 * 1024 * 1024
MAX_SEGMENTS = 50_000

_TIMESTAMP = r"(?:(\d{1,3}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
_CUE_TIMING_RE = re.compile(rf"^\s*{_TIMESTAMP}\s*-->\s*{_TIMESTAMP}")
_INLINE_TIMESTAMP_RE = re.compile(r"<\d{1,3}:\d{2}:\d{2}[.,]\d{3}>|<\d{1,2}:\d{2}[.,]\d{3}>")
_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>|<\d[^>]*>")
_WS_RE = re.compile(r"\s+")


def _to_seconds(h: str | None, m: str, s: str, frac: str) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(frac.ljust(3, "0")[:3]) / 1000


def clean_text(text: str) -> str:
    """Strip markup (<c>, <i>, <v Speaker>, inline timestamps), decode entities,
    collapse whitespace."""
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("​", "").replace("‎", "").replace("‏", "")
    return _WS_RE.sub(" ", text).strip()


def _normalise_newlines(raw: str) -> str:
    return raw[:MAX_CAPTION_CHARS].lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")


def _parse_cues(raw: str) -> list[tuple[float, float, list[str]]]:
    """Shared WebVTT/SRT cue reader: returns (start, end, raw payload lines).

    Reads line by line. Per the WebVTT spec only a truly empty line ends a cue:
    YouTube's auto-captions put whitespace-only lines *inside* cues, so splitting
    on "blank-looking" lines would tear cues apart. Anything outside a cue
    (header, NOTE/STYLE/REGION blocks, SRT index numbers) is skipped.
    """
    cues: list[tuple[float, float, list[str]]] = []
    current: list | None = None  # [start, end, payload lines]
    for line in _normalise_newlines(raw).split("\n"):
        match = _CUE_TIMING_RE.match(line) if "-->" in line else None
        if match:
            if current is not None:
                # A new timing line inside an open cue: the file used a
                # whitespace-only separator. The line just before the timing
                # line is the next cue's identifier, not caption text.
                if current[2] and current[2][-1].strip():
                    current[2].pop()
                cues.append((current[0], current[1], current[2]))
            if len(cues) >= MAX_SEGMENTS:
                return cues
            g = match.groups()
            current = [_to_seconds(*g[0:4]), _to_seconds(*g[4:8]), []]
        elif current is not None:
            if line == "":
                cues.append((current[0], current[1], current[2]))
                current = None
            else:
                current[2].append(line)
    if current is not None and len(cues) < MAX_SEGMENTS:
        cues.append((current[0], current[1], current[2]))
    return cues


def parse_vtt(raw: str) -> list[Segment]:
    cues = _parse_cues(raw)
    # YouTube auto-captions ship as "rolling" VTT: each cue repeats the previous
    # line and adds a new one carrying inline word timestamps. Emitting every
    # cue verbatim would duplicate every line, so in that format we emit each
    # line once, at the cue where it first appears.
    rolling = any(_INLINE_TIMESTAMP_RE.search(line) for _, _, lines in cues for line in lines)
    if not rolling:
        return finalize_segments(
            Segment(start, end, clean_text(" ".join(lines))) for start, end, lines in cues
        )

    segments: list[Segment] = []
    last_line = None
    for start, end, lines in cues:
        for line in lines:
            text = clean_text(line)
            if not text or text == last_line:
                continue
            segments.append(Segment(start, end, text))
            last_line = text
    return finalize_segments(segments)


def parse_srt(raw: str) -> list[Segment]:
    return finalize_segments(
        Segment(start, end, clean_text(" ".join(lines))) for start, end, lines in _parse_cues(raw)
    )


def parse_json3(raw: str) -> list[Segment]:
    """YouTube's json3 format: {"events": [{"tStartMs", "dDurationMs", "segs": [{"utf8"}]}]}.

    Auto-caption json3 carries each word once (unlike rolling VTT); events whose
    only content is a newline are line-break markers and are skipped.
    """
    try:
        data = json.loads(raw[:MAX_CAPTION_CHARS])
    except (ValueError, TypeError):
        return []
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, list):
        return []

    segments = []
    for event in events[:MAX_SEGMENTS]:
        if not isinstance(event, dict) or not isinstance(event.get("segs"), list):
            continue
        text = "".join(str(seg.get("utf8", "")) for seg in event["segs"] if isinstance(seg, dict))
        try:
            start = float(event.get("tStartMs", 0)) / 1000
            end = start + float(event.get("dDurationMs", 0)) / 1000
        except (TypeError, ValueError):
            continue
        segments.append(Segment(start, end, clean_text(text)))
    return finalize_segments(segments)


PARSERS = {"json3": parse_json3, "vtt": parse_vtt, "srt": parse_srt}


def parse_caption_file(raw: str, ext: str) -> list[Segment]:
    parser = PARSERS.get((ext or "").lower())
    return parser(raw) if parser else []


def finalize_segments(segments) -> list[Segment]:
    """Drop empty text, order by time, and make timings safe for SRT/VTT export:
    no negative or zero-length cues, and no cue running past the next one's start
    (platform captions often overlap while a line scrolls)."""
    cleaned = sorted(
        (
            Segment(max(0.0, round(s.start, 3)), max(0.0, round(s.end, 3)), s.text)
            for s in segments
            if s.text
        ),
        key=lambda s: s.start,
    )[:MAX_SEGMENTS]

    for i, seg in enumerate(cleaned):
        next_start = cleaned[i + 1].start if i + 1 < len(cleaned) else None
        if next_start is not None and seg.end > next_start > seg.start:
            seg.end = next_start
        if seg.end <= seg.start:
            fallback = seg.start + 1.0
            if next_start is not None and next_start > seg.start:
                fallback = min(fallback, next_start)
            seg.end = round(fallback, 3)
    return cleaned


_SENTENCE_END_RE = re.compile(r"[.!?…][\"')\]]*$")


def segments_to_paragraphs(
    segments: list[Segment],
    *,
    pause_seconds: float = 2.0,
    soft_limit: int = 500,
    hard_limit: int = 1200,
) -> list[tuple[float, str]]:
    """Group segments into readable paragraphs, returned as (start time, text).

    A new paragraph starts after a pause in speech, after a sentence once the
    paragraph is reasonably long, or unconditionally once it gets very long
    (auto-captions often have no punctuation at all).
    """
    paragraphs: list[tuple[float, str]] = []
    current: list[str] = []
    current_start = 0.0
    length = 0
    prev_end = None
    for seg in segments:
        if current:
            paused = prev_end is not None and seg.start - prev_end >= pause_seconds
            sentence_break = length >= soft_limit and _SENTENCE_END_RE.search(current[-1])
            if paused or sentence_break or length >= hard_limit:
                paragraphs.append((current_start, " ".join(current)))
                current, length = [], 0
        if not current:
            current_start = seg.start
        current.append(seg.text)
        length += len(seg.text) + 1
        prev_end = seg.end
    if current:
        paragraphs.append((current_start, " ".join(current)))
    return paragraphs


def segments_to_text(segments: list[Segment]) -> str:
    return "\n\n".join(text for _, text in segments_to_paragraphs(segments))
