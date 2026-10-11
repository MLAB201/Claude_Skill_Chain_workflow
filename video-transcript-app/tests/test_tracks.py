import pytest

from app.models import NoTranscriptAvailable, TrackInfo
from app.tracks import base_language, choose_track


def manual(lang, name=None):
    return TrackInfo(code=lang, language=lang, name=name or lang, kind="manual")


def auto(lang, original=True):
    return TrackInfo(code=f"a.{lang}", language=lang, name=f"{lang} (auto-generated)", kind="auto", is_original=original)


@pytest.mark.parametrize(
    "code, expected",
    [("en", "en"), ("en-US", "en"), ("eng-US", "en"), ("zh-Hans", "zh"), ("pt_BR", "pt"), ("spa-ES", "es"), ("yue", "yue")],
)
def test_base_language(code, expected):
    assert base_language(code) == expected


def test_prefers_manual_in_preferred_language():
    tracks = [auto("en"), manual("de"), manual("en")]
    assert choose_track(tracks, None, ["en"]).code == "en"


def test_preferred_language_auto_beats_other_language_manual():
    # An English speaker wants English: auto English beats a German translation.
    tracks = [manual("de"), auto("en")]
    assert choose_track(tracks, None, ["en"]).code == "a.en"


def test_falls_back_to_manual_in_spoken_language():
    tracks = [manual("fr"), manual("es"), auto("es")]
    assert choose_track(tracks, None, ["en"]).code == "es"


def test_falls_back_to_original_auto_track():
    assert choose_track([auto("ja")], None, ["en"]).code == "a.ja"


def test_without_known_original_uses_first_track():
    tracks = [auto("eng-US", original=False), auto("spa-ES", original=False)]
    assert choose_track(tracks, None, ["fr"]).code == "a.eng-US"


def test_tiktok_iso639_2_matches_preferred():
    tracks = [auto("spa-ES", original=False), auto("eng-US", original=False)]
    assert choose_track(tracks, None, ["en"]).code == "a.eng-US"


def test_requested_exact_code_wins():
    tracks = [manual("en"), auto("en")]
    assert choose_track(tracks, "a.en", ["en"]).code == "a.en"


def test_requested_base_language_matches_manual_first():
    tracks = [auto("en"), manual("en")]
    assert choose_track(tracks, "en-GB", ["de"]).code == "en"


def test_requested_missing_language_lists_alternatives():
    with pytest.raises(NoTranscriptAvailable) as info:
        choose_track([manual("en"), auto("en")], "ko", ["en"])
    assert "en" in info.value.details[0]


def test_no_tracks():
    with pytest.raises(NoTranscriptAvailable):
        choose_track([], None, ["en"])
