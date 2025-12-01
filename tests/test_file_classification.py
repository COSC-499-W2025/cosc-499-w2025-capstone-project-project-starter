import os
import pytest
from codeparser.file_classification import is_binary_file, list_text_files

def test_is_binary_file_text(tmp_path):
    f = tmp_path / "example.txt"
    f.write_text("sample text")
    assert is_binary_file(str(f)) is False


def test_is_binary_file_binary(tmp_path):
    f = tmp_path / "example.bin"
    f.write_bytes(b"\x00\xFF\x10\x80")
    assert is_binary_file(str(f)) is True


def test_is_binary_file_invalid_path():
    assert is_binary_file("nonexistent.file") is True


def test_list_text_files_simple(tmp_path):
    text1 = tmp_path / "a.txt"
    text2 = tmp_path / "sub" / "b.txt"
    binary1 = tmp_path / "c.bin"

    text1.write_text("hello")
    text2.parent.mkdir()
    text2.write_text("world")
    binary1.write_bytes(b"\x00\x01\x02")

    result = list_text_files(str(tmp_path))

    assert str(text1) in result
    assert str(text2) in result
    assert str(binary1) not in result
