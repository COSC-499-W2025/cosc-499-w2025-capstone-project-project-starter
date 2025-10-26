import json
import os
from pathlib import Path
import tempfile
from codeparser.chunking import (
    _normalize_text,
    _language_from_path,
    chunk,
    iter_text,
    file_to_chunk,
    write_chunks_json,
    EXT_TO_LANG,
)


def test_normalize_text():
    s = "a\r\nb\rc\x00d"
    assert _normalize_text(s) == "a\nb\ncd"


def test_language_from_path():
    assert _language_from_path(Path("a.py")) == "python"
    assert _language_from_path(Path("x.unknownext")) == "unknown"


def test_chunk_basic():
    text = "abcdef"
    chunks = list(chunk(text, max_chars=3, overlap=1))
    assert chunks[0] == (0, 3, "abc")
    assert chunks[1][2].startswith("cd")


def test_chunk_empty():
    assert list(chunk("")) == []



