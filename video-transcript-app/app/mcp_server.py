"""MCP server: lets Claude (the desktop app, Claude Code) or any other MCP client
fetch transcripts with this app's pipeline, on your own computer.

MCP clients start it themselves (see the README):

    /path/to/video-transcript-app/.venv/bin/python /path/to/video-transcript-app/mcp_server.py

By default it speaks MCP over stdin/stdout, so nothing here prints to stdout.
`--http` serves Streamable HTTP on 127.0.0.1 instead, for clients that take a URL.
"""

from __future__ import annotations

import argparse
from typing import Annotated, Optional

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from .config import load_settings
from .models import TranscriptError
from .service import TranscriptService
from .urls import MAX_URL_LENGTH, parse_video_url

SERVER_NAME = "transcripts"

_SOURCES = {
    "manual": "creator captions",
    "auto": "auto-generated captions",
    "speech-to-text": "speech-to-text",
}

settings = load_settings()
service = TranscriptService(settings)

server = MCPServer(
    SERVER_NAME,
    instructions=(
        "Fetches the transcript of a public YouTube or TikTok video on the user's own computer. "
        "Call get_transcript with the video link exactly as the user gave it. The text is the "
        "platform's captions (or local speech-to-text when asked for), never a summary. When a "
        "video has no captions the tool says so; never invent transcript text."
    ),
)


def _clock(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def transcript_text(data: dict, timestamps: bool = True) -> str:
    """The transcript as a model should read it: a short header, then paragraphs."""
    header = []
    if data.get("title"):
        header.append(f"Title: {data['title']}")
    if data.get("author"):
        header.append(f"By: {data['author']}")
    header.append(f"Link: {data['url']}")
    source = _SOURCES.get(data["kind"], data["kind"])
    language = data.get("language_name") or data.get("language")
    header.append(f"Source: {source}" + (f" ({language})" if language else ""))
    length = f"{data['word_count']:,} words"
    if data.get("duration"):
        length = f"{_clock(data['duration'])}, {length}"
    header.append(f"Length: {length}")
    header.extend(f"Note: {note}" for note in data.get("notes") or [])
    body = [f"[{_clock(p['start'])}] {p['text']}" if timestamps else p["text"] for p in data["paragraphs"]]
    return "\n".join(header) + "\n\n" + "\n\n".join(body) + "\n"


def _structured(data: dict) -> dict:
    # Timed lines and metadata for programs (such as the Transcript Puller artifact);
    # the paragraphs and plain text are already in the text content.
    keys = (
        "platform", "video_id", "url", "title", "author", "duration", "language", "language_name",
        "kind", "provider", "word_count", "notes", "segments", "tracks",
    )
    return {key: data[key] for key in keys}


def _error_text(exc: TranscriptError) -> str:
    text = exc.message
    if exc.details:
        text += " (" + "; ".join(exc.details) + ")"
    return f"{text} [{exc.code}]"


@server.tool(
    title="Get video transcript",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def get_transcript(
    url: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_URL_LENGTH,
            description="The YouTube or TikTok video link, e.g. https://youtu.be/... or https://www.tiktok.com/@user/video/...",
        ),
    ],
    language: Annotated[
        Optional[str],
        Field(
            max_length=40,
            pattern=r"^[A-Za-z0-9._-]+$",
            description='Optional caption track code from an earlier result\'s "tracks": "en" for creator captions, "a.en" for auto-captions.',
        ),
    ] = None,
    speech_to_text: Annotated[
        bool,
        Field(description="Transcribe the audio locally when the video has no captions. Slow, and only works if speech-to-text is installed."),
    ] = False,
    timestamps: Annotated[bool, Field(description="Start each paragraph with its [m:ss] time.")] = True,
) -> CallToolResult:
    """Get the full transcript of a YouTube or TikTok video, fetched on this computer."""
    try:
        ref = parse_video_url(url)
        # The pipeline blocks on network calls; keep it off the event loop.
        result = await anyio.to_thread.run_sync(service.get_transcript, ref, language, speech_to_text)
    except TranscriptError as exc:
        raise ToolError(_error_text(exc)) from exc
    data = result.to_dict()
    return CallToolResult(
        content=[TextContent(type="text", text=transcript_text(data, timestamps))],
        structured_content=_structured(data),
    )


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Video transcript MCP server.")
    parser.add_argument("--http", action="store_true", help="serve Streamable HTTP on 127.0.0.1 instead of stdio")
    parser.add_argument("--port", type=int, default=8765, help="port for --http (default 8765)")
    args = parser.parse_args(argv)
    if args.http:
        server.run("streamable-http", host="127.0.0.1", port=args.port)
    else:
        server.run()


if __name__ == "__main__":
    main()
