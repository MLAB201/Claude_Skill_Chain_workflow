"""HTTP API + static frontend.

Run locally:  uvicorn app.main:app --reload   (from the video-transcript-app folder)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import load_settings
from .models import TranscriptError
from .service import TranscriptService
from .urls import MAX_URL_LENGTH, parse_video_url

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

settings = load_settings()
service = TranscriptService(settings)

app = FastAPI(
    title="Video Transcript Puller",
    version="1.0.0",
    description="Pull transcripts from YouTube and TikTok videos.",
)

_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' https: data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def _error(status: int, code: str, message: str, details: Optional[list[str]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


@app.exception_handler(TranscriptError)
async def transcript_error_handler(request: Request, exc: TranscriptError):
    return _error(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [f"{'.'.join(str(p) for p in e.get('loc', [])[1:])}: {e.get('msg')}" for e in exc.errors()]
    return _error(400, "invalid_request", "The request was malformed.", details)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return _error(500, "internal_error", "Something went wrong on the server. Check the server log.")


class TranscriptRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    language: Optional[str] = Field(None, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    speech_to_text: bool = False


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "speech_to_text": service.speech_to_text_available(),
        "speech_to_text_max_minutes": settings.whisper_max_duration // 60,
    }


# A plain `def` route: FastAPI runs it in a worker thread, so the blocking
# network calls inside don't stall the event loop.
@app.post("/api/transcript")
def transcript(body: TranscriptRequest):
    ref = parse_video_url(body.url)
    result = service.get_transcript(ref, body.language, body.speech_to_text)
    return result.to_dict()


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
