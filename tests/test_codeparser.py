import pytest
from unittest.mock import patch
from codeparser.file_classification import is_binary_file, list_text_files
from pathlib import Path
from codeparser.chunking import chunk, _normalize_text, _language_from_path, iter_text, write_chunks_json
import json

def test_is_binary_file_with_text(tmp_path):
    # Create a real text file
    f = tmp_path / "hello.txt"
    f.write_text("this is a text file")
    assert is_binary_file(str(f)) is False

def test_is_binary_file_with_binary(tmp_path):
    # Create a file with bytes that typically trigger binary detection
    f = tmp_path / "image.bin"
    f.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    assert is_binary_file(str(f)) is True

def test_is_binary_file_exception_fallback():
    # Mock magic.from_file to raise an Exception to hit the except block
    with patch("magic.from_file", side_effect=Exception("MIME failure")):
        assert is_binary_file("some_weird_path") is True

def test_list_text_files(tmp_path):
    # Setup a nested directory structure
    subdir = tmp_path / "sub"
    subdir.mkdir()
    
    txt_file = tmp_path / "valid.txt"
    txt_file.write_text("hello")
    
    inner_txt = subdir / "inner.txt"
    inner_txt.write_text("world")
    
    bin_file = tmp_path / "logo.png"
    bin_file.write_bytes(b"\x00\xFF\x00\xFF") # Fake binary
    
    # Run the function
    results = list_text_files(str(tmp_path))
    
    # Check that it found both text files but skipped the binary one
    assert len(results) == 2
    assert any("valid.txt" in p for p in results)
    assert any("inner.txt" in p for p in results)
    assert not any("logo.png" in p for p in results)

def test_chunk_logic():
    text = "ABCDEFGHIJ"  # 10 chars
    # Max 4 chars, overlap 2
    # Chunk 1: ABCD (0,4)
    # Chunk 2: CDEF (2,6) ... starts at end(4) - overlap(2) = 2
    chunks = list(chunk(text, max_chars=4, overlap=2))
    assert chunks[0] == (0, 4, "ABCD")
    assert chunks[1] == (2, 6, "CDEF")
    assert chunks[-1][1] == 10 # Should end at string length

def test_normalize_text():
    assert _normalize_text("line1\r\nline2\x00") == "line1\nline2"

def test_language_from_path():
    assert _language_from_path(Path("test.py")) == "python"
    assert _language_from_path(Path("README.md")) == "markdown"
    assert _language_from_path(Path("unknown.xyz")) == "unknown"

def test_iter_text_skips_excludes(tmp_path):
    # Setup: one good file, one in a skipped folder
    (tmp_path / "good.py").write_text("print(1)")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("bad file")
    
    # Mock is_binary_file to always return False
    is_bin = lambda x: False
    
    found_files = list(iter_text(tmp_path, is_bin))
    assert len(found_files) == 1
    assert found_files[0].name == "good.py"

def test_write_chunks_json(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    code_file = repo / "main.py"
    # Create text long enough to force at least 2 chunks
    code_file.write_text("A" * 3000) 
    
    out_json = tmp_path / "output.jsonl"
    
    count = write_chunks_json(
        repo_root=str(repo),
        out_json=str(out_json),
        is_binary_file=lambda x: False,
        max_chars=2000,
        overlap=200
    )
    
    assert count >= 2
    assert out_json.exists()
    
    # Verify JSON structure of the first line
    with open(out_json, "r") as f:
        first_line = json.loads(f.readline())
        assert "repo_relpath" in first_line
        assert first_line["language"] == "python"
        assert first_line["text"] == "A" * 2000