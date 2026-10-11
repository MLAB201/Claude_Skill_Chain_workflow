import http.server
import json
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from app.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def settings():
    # Cache off so every test exercises the real path.
    return Settings(cache_ttl_seconds=0, socket_timeout=5)


class FakeYouTube(BaseAdapter):
    """A requests adapter that answers like YouTube, from recorded fixtures."""

    def __init__(self, innertube="youtube_innertube_ok.json", oembed=None, fail=None):
        super().__init__()
        self.innertube = innertube
        self.oembed = oembed
        self.fail = fail
        self.calls = []

    def send(self, request, **kwargs):
        self.calls.append((request.method, request.url))
        if self.fail:
            raise self.fail
        parts = urlsplit(request.url)
        if parts.path == "/watch":
            return self._response(request, 200, fixture_text("youtube_watch_page.html"))
        if parts.path == "/youtubei/v1/player":
            return self._response(request, 200, fixture_text(self.innertube))
        if parts.path == "/api/timedtext":
            return self._response(request, 200, fixture_text("youtube_timedtext.xml"))
        if parts.path == "/oembed":
            if self.oembed is None:
                return self._response(request, 404, "Not Found")
            return self._response(request, 200, json.dumps(self.oembed))
        return self._response(request, 404, "Not Found")

    def close(self):
        pass

    @staticmethod
    def _response(request, status, body):
        resp = requests.Response()
        resp.status_code = status
        resp._content = body.encode("utf-8")
        resp.encoding = "utf-8"
        resp.url = request.url
        resp.request = request
        resp.headers["Content-Type"] = "application/json" if body.startswith("{") else "text/html"
        return resp

    def timedtext_langs(self):
        langs = []
        for method, url in self.calls:
            parts = urlsplit(url)
            if parts.path == "/api/timedtext":
                q = parse_qs(parts.query)
                langs.append((q.get("lang", [None])[0], q.get("kind", [None])[0]))
        return langs


def fake_youtube_session(adapter: FakeYouTube) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class _Handler(http.server.BaseHTTPRequestHandler):
    routes: dict = {}
    hits: list = []

    def do_GET(self):
        type(self).hits.append(self.path)
        body = type(self).routes.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    """A throwaway HTTP server on 127.0.0.1. Set `.routes[path] = bytes`."""
    handler = type("Handler", (_Handler,), {"routes": {}, "hits": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    server.routes = handler.routes
    server.hits = handler.hits
    yield server
    server.shutdown()
    server.server_close()
