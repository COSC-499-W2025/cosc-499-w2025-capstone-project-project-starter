"""
test_zip_parser.py
-------------------
Unit tests for the ZIP ingest pipeline to validate both low-level parsing (`parse_zip`)
and the pure integration function (`categorize_parse_zip`) that returns a unified
dictionary of ZIP metadata, per-file info, and categorized folder contents.
Verifies handling of empty, invalid, and corrupt ZIPs; checks schema/keys; and
cross-validates that files in `file_info` appear in `categorized_contents`.
(No filesystem writes; the function under test is pure and returns a dict.)

Run from root directory with:
    docker compose run --rm backend python3 -m pytest tests/ingest/test_zip_parser.py -v
    or 
    python3 -m pytest tests/ingest/test_zip_parser.py -v
    (Optional) Test coverage with:
        docker compose run --rm backend pytest tests/ingest/test_zip_parser.py --cov=src/ingest --cov=src/categorize --cov-report=term-missing -v
        * 87% coverage *
"""


import pytest
import zipfile
import json
from pathlib import Path

from src.ingest.zip_parser import parse_zip, categorize_parse_zip, ZipParseError
from src.ingest.models import ZipIndex, ZipEntry


class TestZipParser:
    def test_parses_simple_zip(self, tmp_path):
        """Test parsing a zip with a single text file."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("readme.txt", "Hello World")
        
        result = parse_zip(zip_path)
        
        assert isinstance(result, ZipIndex)
        assert result.root_name == "test.zip"
        assert result.file_count == 1
        assert len(result.files) == 1
        
        file_entry = result.files[0]
        assert file_entry.rel_path == "readme.txt"
        assert file_entry.ext == "txt"
        assert file_entry.depth == 0
        assert len(file_entry.sha256) == 64

    def test_handles_empty_zip(self, tmp_path):
        """Test parsing an empty zip file."""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            pass  # Create empty zip
        
        result = parse_zip(zip_path)
        
        assert result.file_count == 0
        assert result.files == []

    def test_raises_error_for_invalid_zip(self, tmp_path):
        """Test that invalid files raise ZipParseError."""
        zip_path = tmp_path / "not_a_zip.txt"
        zip_path.write_text("This is not a zip file")
        
        with pytest.raises(ZipParseError):
            parse_zip(zip_path)

    def test_raises_error_for_missing_file(self, tmp_path):
        """Test that missing files raise ZipParseError."""
        zip_path = tmp_path / "nonexistent.zip"
        
        with pytest.raises(ZipParseError):
            parse_zip(zip_path)


@pytest.fixture
def sample_zip_path(tmp_path):
    """
    Create a temporary ZIP file with a variety of files and extensions
    to test categorize_parse_zip.
    Structure:
      README.md              -> documentation
      src/main.py            -> code (python)
      design/diagram.drawio  -> sketches
      assets/logo.png        -> images
    """
    zip_path = tmp_path / "sample_project.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("README.md", "# Demo Project\n")
        zf.writestr("src/main.py", "print('Hello')\n")
        zf.writestr("design/diagram.drawio", "<drawio/>")
        zf.writestr("assets/logo.png", b"\x89PNG\r\n\x1a\n")
    return zip_path


class TestCategorizeParser:
    def test_returns_expected_structure(self, sample_zip_path):
        """Ensure categorize_parse_zip returns expected structure."""
        result = categorize_parse_zip(sample_zip_path)

        # Top-level type & keys
        assert isinstance(result, dict)
        assert set(result.keys()) == {"zip_metadata", "file_info", "categorized_contents"}

        # Metadata checks
        meta = result["zip_metadata"]
        assert meta["root_name"] == "sample_project.zip"
        assert meta["file_count"] == 4
        assert meta["total_uncompressed_bytes"] > 0
        assert meta["total_compressed_bytes"] > 0

        # File info section
        files = result["file_info"]
        assert isinstance(files, list)
        assert all("rel_path" in f and "size" in f for f in files)
        assert any(f["rel_path"].endswith("main.py") for f in files)

        # Categorized contents section
        categorized = result["categorized_contents"]
        assert isinstance(categorized, dict)
        flat_json = json.dumps(categorized)
        for category in ["code", "documentation", "images", "sketches", "other"]:
            assert category in flat_json

    def test_empty_or_invalid_zip_returns_empty_dict(self, tmp_path):
        """If the ZIP path is invalid or empty, the function should return {}."""
        bad_zip = tmp_path / "does_not_exist.zip"
        result = categorize_parse_zip(bad_zip)
        assert result == {}

        # Empty but valid ZIP
        empty_zip = tmp_path / "empty.zip"
        with zipfile.ZipFile(empty_zip, "w"):
            pass
        result2 = categorize_parse_zip(empty_zip)
        assert isinstance(result2, dict)
        assert result2["zip_metadata"]["file_count"] == 0

    def test_corrupt_zip_returns_empty_dict(self, tmp_path):
        """Corrupt ZIP file should not crash, should return {}."""
        corrupt_zip = tmp_path / "corrupt.zip"
        corrupt_zip.write_bytes(b"not-a-real-zip")
        result = categorize_parse_zip(corrupt_zip)
        assert result == {}

    def test_file_info_matches_categorization(self, sample_zip_path):
        """Ensure all file names appear in both metadata and categorized output."""
        result = categorize_parse_zip(sample_zip_path)
        file_names = {Path(f["rel_path"]).name for f in result["file_info"]}
        all_categorized = json.dumps(result["categorized_contents"])
        for fname in file_names:
            assert fname in all_categorized, f"{fname} missing from categorized structure"