import pytest
from parser.parser import parse_directory, summarize_results


def test_parse_directory_basic(tmp_path):
    # Create one text file and one binary file
    text_file = tmp_path / "a.txt"
    binary_file = tmp_path / "b.bin"

    text_file.write_text("some text here")
    binary_file.write_bytes(b"\x00\xFF\x00")

    summary = parse_directory(str(tmp_path))

    assert summary["total_files"] == 2
    assert any("a.txt" in p for p in summary["text_files"])
    assert any("b.bin" in p for p in summary["binary_files"])
    assert len(summary["binary_files"]) == 1
    assert len(summary["text_files"]) == 1


def test_parse_directory_nested(tmp_path):
    # Create nested directory structure with one text and one binary file
    subdir = tmp_path / "nested"
    subdir.mkdir()
    file1 = subdir / "file1.txt"
    file2 = tmp_path / "root.bin"

    file1.write_text("nested text")
    file2.write_bytes(b"\x00\x01\x02")

    summary = parse_directory(str(tmp_path))
    assert summary["total_files"] == 2
    assert any("file1.txt" in p for p in summary["text_files"])
    assert any("root.bin" in p for p in summary["binary_files"])


def test_parse_directory_missing():
    # Directory does not exist should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        parse_directory("nonexistent_dir")


def test_summarize_results_output(capsys):
    # Fake summary to test printed output formatting
    summary = {
        "total_files": 3,
        "binary_files": ["a.bin"],
        "text_files": ["b.txt", "c.txt"]
    }

    summarize_results(summary)
    captured = capsys.readouterr()

    assert "Total files scanned: 3" in captured.out
    assert "Binary files       : 1" in captured.out
    assert "Text files         : 2" in captured.out
