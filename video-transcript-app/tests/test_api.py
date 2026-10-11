import pytest
from fastapi.testclient import TestClient

from app import main
from app.models import Segment, TranscriptResult, UpstreamBlocked, VideoMeta


@pytest.fixture
def client():
    return TestClient(main.app, raise_server_exceptions=False)


def fake_result(ref):
    return TranscriptResult(
        platform=ref.platform,
        video_id=ref.video_id,
        url=ref.url,
        track_code="en",
        language="en",
        language_name="English",
        kind="manual",
        provider="test",
        segments=[Segment(0.0, 2.0, "first line"), Segment(5.0, 6.0, "second <b>line</b>")],
        meta=VideoMeta(title="A video", author="Someone", duration=6.0),
    )


def test_frontend_is_served_with_security_headers(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Transcript Puller" in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    for asset in ("/js/app.js", "/js/formats.js", "/css/styles.css", "/favicon.svg"):
        assert client.get(asset).status_code == 200, asset


def test_health(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert isinstance(data["speech_to_text"], bool)


def test_transcript_success(client, monkeypatch):
    seen = {}

    def fake(ref, language, speech_to_text):
        seen.update(ref=ref, language=language, stt=speech_to_text)
        return fake_result(ref)

    monkeypatch.setattr(main.service, "get_transcript", fake)
    resp = client.post(
        "/api/transcript",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "language": "a.en", "speech_to_text": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert seen["ref"].video_id == "dQw4w9WgXcQ" and seen["language"] == "a.en" and seen["stt"] is True
    assert data["title"] == "A video"
    assert data["segments"][1] == {"start": 5.0, "end": 6.0, "text": "second <b>line</b>"}
    assert data["paragraphs"] == [
        {"start": 0.0, "text": "first line"},
        {"start": 5.0, "text": "second <b>line</b>"},
    ]
    assert data["text"] == "first line\n\nsecond <b>line</b>"


@pytest.mark.parametrize(
    "body, code",
    [
        ({"url": "https://vimeo.com/123"}, "invalid_url"),
        ({"url": "https://www.youtube.com/playlist?list=PL1"}, "invalid_url"),
        ({"url": "https://youtu.be/dQw4w9WgXcQ", "language": "../../etc"}, "invalid_request"),
        ({"url": ""}, "invalid_request"),
        ({}, "invalid_request"),
    ],
)
def test_bad_requests(client, body, code):
    resp = client.post("/api/transcript", json=body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == code


def test_upstream_errors_have_a_stable_shape(client, monkeypatch):
    def fake(ref, language, speech_to_text):
        raise UpstreamBlocked("YouTube is blocking this server.", details=["HTTP 429"])

    monkeypatch.setattr(main.service, "get_transcript", fake)
    resp = client.post("/api/transcript", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert resp.status_code == 503
    assert resp.json() == {
        "error": {"code": "upstream_blocked", "message": "YouTube is blocking this server.", "details": ["HTTP 429"]}
    }


def test_unexpected_errors_do_not_leak_internals(client, monkeypatch):
    def fake(ref, language, speech_to_text):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(main.service, "get_transcript", fake)
    resp = client.post("/api/transcript", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "internal_error"
    assert "secret" not in resp.text
