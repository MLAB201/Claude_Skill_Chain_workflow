import anyio
import pytest
from mcp import Client

from app import mcp_server
from app.models import Segment, TranscriptResult, UpstreamBlocked, VideoMeta


def fake_result(ref):
    return TranscriptResult(
        platform=ref.platform,
        video_id=ref.video_id,
        url=ref.url,
        track_code="a.en",
        language="en",
        language_name="English",
        kind="auto",
        provider="test",
        segments=[Segment(0.0, 2.0, "first line"), Segment(65.0, 66.0, "second line")],
        meta=VideoMeta(title="A video", author="Someone", duration=3725.0),
    )


def run(coro_fn):
    return anyio.run(coro_fn)


@pytest.fixture
def fake_service(monkeypatch):
    seen = {}

    def fake(ref, language, speech_to_text):
        seen.update(ref=ref, language=language, stt=speech_to_text)
        return fake_result(ref)

    monkeypatch.setattr(mcp_server.service, "get_transcript", fake)
    return seen


def test_lists_one_read_only_tool():
    async def go():
        async with Client(mcp_server.server) as client:
            return (await client.list_tools()).tools

    (tool,) = run(go)
    assert tool.name == "get_transcript"
    assert tool.annotations.read_only_hint is True
    assert tool.input_schema["required"] == ["url"]
    assert set(tool.input_schema["properties"]) == {"url", "language", "speech_to_text", "timestamps"}


def test_returns_readable_text_and_timed_lines(fake_service):
    async def go():
        async with Client(mcp_server.server) as client:
            return await client.call_tool("get_transcript", {"url": "https://youtu.be/dQw4w9WgXcQ?si=x", "language": "a.en"})

    result = run(go)
    assert not result.is_error
    assert fake_service["ref"].video_id == "dQw4w9WgXcQ"
    assert fake_service["language"] == "a.en" and fake_service["stt"] is False
    text = result.content[0].text
    assert text.startswith(
        "Title: A video\nBy: Someone\nLink: https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
        "Source: auto-generated captions (English)\nLength: 1:02:05, 4 words\n\n"
    )
    assert "[0:00] first line" in text and "[1:05] second line" in text
    data = result.structured_content
    assert data["segments"] == [
        {"start": 0.0, "end": 2.0, "text": "first line"},
        {"start": 65.0, "end": 66.0, "text": "second line"},
    ]
    assert data["title"] == "A video" and data["kind"] == "auto"


def test_timestamps_can_be_left_out(fake_service):
    async def go():
        async with Client(mcp_server.server) as client:
            return await client.call_tool("get_transcript", {"url": "https://youtu.be/dQw4w9WgXcQ", "timestamps": False})

    text = run(go).content[0].text
    assert "[0:00]" not in text and "first line" in text


def test_bad_link_is_a_tool_error_with_its_code(fake_service):
    async def go():
        async with Client(mcp_server.server) as client:
            return await client.call_tool("get_transcript", {"url": "https://example.com/video"})

    result = run(go)
    assert result.is_error
    assert "[invalid_url]" in result.content[0].text
    assert "ref" not in fake_service


def test_pipeline_errors_reach_the_caller(monkeypatch):
    def blocked(ref, language, speech_to_text):
        raise UpstreamBlocked("YouTube is blocking requests from this computer.", details=["HTTP 429"])

    monkeypatch.setattr(mcp_server.service, "get_transcript", blocked)

    async def go():
        async with Client(mcp_server.server) as client:
            return await client.call_tool("get_transcript", {"url": "https://www.tiktok.com/t/ZPLARkbvM/"})

    result = run(go)
    assert result.is_error
    assert "YouTube is blocking requests from this computer. (HTTP 429) [upstream_blocked]" in result.content[0].text
