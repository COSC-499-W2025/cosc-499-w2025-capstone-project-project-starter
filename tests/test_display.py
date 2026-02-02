# tests/test_display.py
from __future__ import annotations

import io
from dataclasses import dataclass
from unittest.mock import patch

import src.cli.display as display


@dataclass
class ObjResult:
    error_type: str = "INVALID_ZIP"
    message: str = "bad zip"
    data: dict | None = None


def test_display_error_accepts_dict_and_prints_error_type_and_message() -> None:
    result = {
        "error_type": "INVALID_ZIP",
        "message": "bad zip",
        "data": {"hint": "upload a real .zip"},
    }

    buf = io.StringIO()
    with patch("sys.stdout", buf):
        display.display_error(result)

    out = buf.getvalue()
    assert "Error Type" in out
    assert "INVALID_ZIP" in out
    assert "bad zip" in out
    assert "hint" in out


def test_display_error_accepts_object_and_prints_error_type_and_message() -> None:
    result = ObjResult(data={"foo": "bar"})

    buf = io.StringIO()
    with patch("sys.stdout", buf):
        display.display_error(result)

    out = buf.getvalue()
    assert "INVALID_ZIP" in out
    assert "bad zip" in out
    assert "foo" in out


def test_display_success_accepts_dict_and_prints_basic_fields() -> None:
    result = {
        "message": "uploaded",
        "data": {"filename": "test.zip", "file_id": 123, "files": ["a.py", "b.py"]},
    }

    buf = io.StringIO()
    with patch("sys.stdout", buf):
        display.display_success(result)

    out = buf.getvalue()
    assert "SUCCESS" in out
    assert "uploaded" in out
    assert "test.zip" in out
    assert "123" in out
