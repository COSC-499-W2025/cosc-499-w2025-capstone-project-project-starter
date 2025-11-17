import pytest
import os
import tempfile
from codeparser.file_classification import is_binary_file, scan_directory_for_binaries

def test_is_binary_file_text(tmp_path):
    text_file = tmp_path / "example.txt"
    text_file.write_text("print('hello world')")
    assert is_binary_file(str(text_file)) is False


def test_is_binary_file_binary(tmp_path):
    binary_file = tmp_path / "example.bin"
    binary_file.write_bytes(b"\x00\xFF\x00\x10")
    assert is_binary_file(str(binary_file)) is True


#rn this just makes sure it prints out the right stuff, we can change later
def test_scan_directory_for_binaries(capsys, tmp_path):
    text_file = tmp_path / "a.txt"
    binary_file = tmp_path / "b.bin"
    text_file.write_text("some text content")
    binary_file.write_bytes(b"\x00\x01\x02")

    scan_directory_for_binaries(str(tmp_path))
    captured = capsys.readouterr()

    assert "a.txt" in captured.out
    assert "b.bin" in captured.out

    assert "False" in captured.out
    assert "True" in captured.out


def test_is_binary_file_invalid_path():
    assert is_binary_file("nonexistent.file") is True