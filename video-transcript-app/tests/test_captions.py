import pytest

from app.captions import (
    finalize_segments,
    parse_caption_file,
    parse_json3,
    parse_srt,
    parse_vtt,
    segments_to_paragraphs,
    segments_to_text,
)
from app.models import Segment

from conftest import fixture_text


def triples(segments):
    return [(s.text, s.start, s.end) for s in segments]


def test_youtube_rolling_vtt_emits_each_line_once():
    segments = parse_vtt(fixture_text("youtube_auto_rolling.vtt"))
    assert triples(segments) == [
        ("hey everyone welcome back", 0.16, 2.149),
        ("to the channel today", 2.159, 4.789),
        ("we're talking about R&D", 4.799, 7.43),
        ("[Music]", 10.0, 12.0),
    ]


def test_manual_vtt_strips_markup_and_keeps_repeated_lines():
    segments = parse_vtt(fixture_text("manual.vtt"))
    assert triples(segments) == [
        ("Welcome to the show.", 1.0, 3.5),
        ("Today: cats & dogs — and <birds>", 3.5, 6.0),
        # Not rolling captions, so a genuinely repeated line must survive.
        ("No.", 62.25, 64.0),
        ("No.", 64.0, 65.0),
    ]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_srt(newline):
    raw = fixture_text("tiktok.srt").replace("\n", newline)
    assert triples(parse_srt(raw)) == [
        ("POV: you finally", 0.12, 1.98),
        ("found the perfect coffee", 1.98, 4.5),
        ("shop", 4.5, 5.5),  # zero-length cue widened so players show it
    ]


def test_json3_auto_captions():
    segments = parse_json3(fixture_text("youtube_auto.json3"))
    assert triples(segments) == [
        # overlapping display windows are clamped to the next line's start
        ("hey everyone welcome back", 0.16, 2.159),
        ("to the channel today", 2.159, 4.799),
        ("we're talking about R&D", 4.799, 7.43),
    ]


def test_bom_and_short_timestamps():
    raw = "﻿WEBVTT\n\n00:01.500 --> 00:03.000\nshort form\n"
    assert triples(parse_vtt(raw)) == [("short form", 1.5, 3.0)]


@pytest.mark.parametrize(
    "parser, raw",
    [
        (parse_json3, "not json"),
        (parse_json3, '{"events": "nope"}'),
        (parse_json3, "[1, 2, 3]"),
        (parse_json3, '{"events": [{"segs": [{"utf8": "x"}], "tStartMs": "bad"}]}'),
        (parse_vtt, "WEBVTT\n\ngarbage --> more garbage\ntext\n"),
        (parse_vtt, ""),
        (parse_srt, "1\nnot a timing line\nhello\n"),
    ],
)
def test_malformed_input_yields_no_segments(parser, raw):
    assert parser(raw) == []


def test_unknown_format_is_not_guessed():
    assert parse_caption_file("anything", "ttml") == []
    assert parse_caption_file("anything", "") == []


def test_finalize_orders_clamps_and_drops_empty():
    out = finalize_segments(
        [
            Segment(5.0, 9.0, "b"),
            Segment(-1.0, 6.0, "a"),
            Segment(7.0, 7.0, ""),
            Segment(9.5, 9.0, "c"),
        ]
    )
    assert triples(out) == [("a", 0.0, 5.0), ("b", 5.0, 9.0), ("c", 9.5, 10.5)]


def test_paragraphs_break_on_pauses_and_length():
    segs = [Segment(0, 1, "one."), Segment(1, 2, "two"), Segment(5, 6, "after a pause")]
    assert segments_to_paragraphs(segs) == [(0, "one. two"), (5, "after a pause")]

    long_run = [Segment(i, i + 1, "word " * 30) for i in range(20)]  # no punctuation, no pauses
    paragraphs = segments_to_paragraphs([Segment(s.start, s.end, s.text.strip()) for s in long_run])
    assert len(paragraphs) > 1
    assert all(len(text) <= 1200 + 150 for _, text in paragraphs)


def test_text_is_paragraphs_joined():
    segs = [Segment(0, 1, "a"), Segment(4, 5, "b")]
    assert segments_to_text(segs) == "a\n\nb"


def test_srt_with_whitespace_only_separators():
    raw = "1\n00:00:01,000 --> 00:00:02,000\nhello\n \n2\n00:00:02,000 --> 00:00:03,000\nworld\n"
    assert triples(parse_srt(raw)) == [("hello", 1.0, 2.0), ("world", 2.0, 3.0)]
