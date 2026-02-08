import os
import httpx
import inspect
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.projects.api import router


if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    _orig_httpx_init = httpx.Client.__init__

    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_init


def _mk_app():
    app = FastAPI()
    app.include_router(router)
    return app


def test_get_thumbnail_form_renders():
    client = TestClient(_mk_app())
    resp = client.get("/projects/demo/thumbnail")
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "<form" in text and "type=\"file\"" in text


def test_upload_thumbnail_png_success():
    client = TestClient(_mk_app())
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 128
    files = {"file": ("thumb.png", png_bytes, "image/png")}
    resp = client.post("/projects/demo/thumbnail", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["project"] == "demo"
    assert body["filename"] == "thumb.png"
    assert body["content_type"] == "image/png"
    assert body["size"] == len(png_bytes)


def test_upload_thumbnail_rejects_invalid_type():
    client = TestClient(_mk_app())
    files = {"file": ("note.txt", b"hello", "text/plain")}
    resp = client.post("/projects/demo/thumbnail", files=files)
    assert resp.status_code == 400
    assert "Invalid file type" in resp.text


def test_upload_thumbnail_rejects_large_file():
    client = TestClient(_mk_app())
    big = b"0" * (5 * 1024 * 1024 + 1)
    files = {"file": ("big.jpg", big, "image/jpeg")}
    resp = client.post("/projects/demo/thumbnail", files=files)
    assert resp.status_code == 400
    assert "File too large" in resp.text
