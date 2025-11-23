# tests/test_analyzer.py
import pytest
from analyzer import analyze_project
from pathlib import Path

def test_analyze_project_empty(tmp_path):
    summary = analyze_project(tmp_path)
    assert summary["total_files"] == 0
    assert summary["binary_files"] == []
    assert summary["text_files"] == []

def test_analyze_project_with_text(tmp_path):
    file1 = tmp_path / "file1.py"
    file1.write_text("print('hello')")
    summary = analyze_project(tmp_path)
    assert summary["total_files"] == 1
    assert len(summary["text_files"]) == 1
    assert "file1.py" in summary["text_files"]

def test_analyze_project_with_binary(tmp_path):
    file1 = tmp_path / "file1.bin"
    file1.write_bytes(b"\x00\x01\x02")
    summary = analyze_project(tmp_path)
    assert summary["total_files"] == 1
    assert len(summary["binary_files"]) == 1
    assert "file1.bin" in summary["binary_files"]
