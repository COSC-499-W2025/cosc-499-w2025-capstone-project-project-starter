import pytest
import os
from parser.parser import parse_directory, summarize_results
from parser import parser
from pathlib import Path


def test_parse_directory_empty(tmp_path):
    """Test parsing an empty directory."""
    summary = parse_directory(str(tmp_path))
    assert summary["total_files"] == 0
    assert len(summary["binary_files"]) == 0
    assert len(summary["text_files"]) == 0


def test_parse_directory_with_unreadable_file(tmp_path, monkeypatch):
    from parser import parser  # patch here, not file_classification

    text_file = tmp_path / "readable.txt"
    bad_file = tmp_path / "badfile.txt"

    text_file.write_text("normal text")
    bad_file.write_text("should raise error")

    def fake_is_binary_file(path):
        if "badfile" in path:
            raise RuntimeError("Simulated read error")
        return False

    monkeypatch.setattr(parser, "is_binary_file", fake_is_binary_file)

    summary = parser.parse_directory(str(tmp_path))

    assert summary["total_files"] == 2
    assert any("badfile.txt" in f for f in summary["binary_files"])
    assert any("readable.txt" in f for f in summary["text_files"])


def test_yield_all_files(tmp_path):
    # Setup files and subdirs with files and symlinks
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.bin"
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    file3 = subdir / "file3.txt"
    file1.write_text("hello")
    file2.write_bytes(b"\x00\x01")
    file3.write_text("world")

    symlink = tmp_path / "link_to_file3.txt"
    try:
        symlink.symlink_to(file3)
        symlink_created = True
    except (NotImplementedError, OSError):
        symlink_created = False

    # Collect yielded files (absolute paths)
    yielded_files = [os.path.abspath(f) for f in parser._yield_all_files(str(tmp_path))]

    # Expected files (absolute paths)
    expected_files = [os.path.abspath(str(f)) for f in [file1, file2, file3]]
    if symlink_created:
        expected_files.append(os.path.abspath(str(symlink)))

    print("\nYielded files:")
    for f in yielded_files:
        print(f)
    print("\nExpected files:")
    for f in expected_files:
        print(f)

    # Check each expected file is in yielded files
    for path in expected_files:
        assert path in yielded_files, f"Expected file {path} not found in yielded files"



def test_summarize_results_empty(capsys):
    """Test summarize_results with an empty summary dictionary."""
    summary = {
        "total_files": 0,
        "binary_files": [],
        "text_files": []
    }
    summarize_results(summary)
    captured = capsys.readouterr()
    assert "Total files scanned: 0" in captured.out
    assert "Binary files       : 0" in captured.out
    assert "Text files         : 0" in captured.out
