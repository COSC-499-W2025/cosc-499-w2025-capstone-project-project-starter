import os
import pytest
from codeparser import metadata_parser

@pytest.fixture
def setup_files(tmp_path):
    # Create a sample text file
    text_file = tmp_path / "sample.txt"
    text_file.write_text("Hello world!")

    # Create a sample binary file
    binary_file = tmp_path / "sample.bin"
    binary_file.write_bytes(b"\x00\xFF\x00\xFF")

    return text_file, binary_file

def test_extract_metadata_keys(setup_files):
    text_file, _ = setup_files
    metadata = metadata_parser.extract_metadata(str(text_file))
    expected_keys = ["file_name", "file_path", "file_size", 
                     "file_extension", "mime_type", "last_modified"]
    for key in expected_keys:
        assert key in metadata

def test_metadata_values(setup_files):
    text_file, _ = setup_files
    metadata = metadata_parser.extract_metadata(str(text_file))
    assert metadata["file_name"] == "sample.txt"
    assert metadata["file_size"] > 0
    assert metadata["file_extension"] == ".txt"
