"""The installable-app (PWA) pieces: manifest, icons, service worker."""

import re
import struct
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parent.parent / "static"
client = TestClient(app)


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", header[16:24])


def test_manifest_is_installable_and_a_share_target():
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    manifest = resp.json()
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    # Android needs a 192px and a 512px PNG icon; a maskable one avoids a white box.
    sizes = {(i["sizes"], i.get("purpose", "any")) for i in manifest["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= sizes
    for icon in manifest["icons"]:
        w, h = png_size(STATIC / icon["src"].lstrip("/"))
        assert f"{w}x{h}" == icon["sizes"]
        assert client.get(icon["src"]).status_code == 200
    share = manifest["share_target"]
    assert share["action"] == "/" and share["method"] == "GET"
    assert share["params"] == {"title": "title", "text": "text", "url": "url"}


def test_page_links_the_manifest():
    html = client.get("/").text
    assert '<link rel="manifest" href="/manifest.json">' in html


def test_service_worker_is_served_from_the_root():
    resp = client.get("/sw.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
    # Everything it pre-caches must exist, or installation of the worker fails.
    block = resp.text.split("const SHELL", 1)[1].split("];", 1)[0]
    shell = re.findall(r'"(/[^"]*)"', block)
    assert "/" in shell and "/js/app.js" in shell
    for path in shell:
        assert client.get(path).status_code == 200, path
