import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from analyzer import analyze_repo


@pytest.fixture
def fake_repo(tmp_path):
    """Create a temporary fake repository for testing."""
    # Create some files
    (tmp_path / "file1.py").write_text("print('Hello world')\n")
    (tmp_path / "file2.txt").write_text("Just some text\n")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
    return tmp_path


@patch("analyzer.parse_directory")
@patch("analyzer.write_chunks_json")
def test_analyze_repo_success(mock_write_chunks, mock_parse_dir, fake_repo):
    """Test successful analysis of a repo directory."""
    mock_parse_dir.return_value = {
        "total_files": 3,
        "binary_files": [str(fake_repo / "binary.bin")],
        "text_files": [str(fake_repo / "file1.py"), str(fake_repo / "file2.txt")]
    }
    mock_write_chunks.return_value = 5

    summary, chunks_written = analyze_repo(str(fake_repo), out_json="out.jsonl")

    # Assertions
    mock_parse_dir.assert_called_once_with(str(fake_repo))
    mock_write_chunks.assert_called_once()
    assert summary["total_files"] == 3
    assert chunks_written == 5


@patch("analyzer.parse_directory", side_effect=FileNotFoundError("Missing directory"))
def test_analyze_repo_missing_directory(mock_parse_dir):
    """Ensure proper handling of missing directory."""
    with pytest.raises(FileNotFoundError):
        analyze_repo("nonexistent_path")


@patch("analyzer.parse_directory", return_value={"total_files": 0, "binary_files": [], "text_files": []})
@patch("analyzer.write_chunks_json", side_effect=Exception("Chunk writing failed"))
def test_analyze_repo_chunk_failure(mock_write_chunks, mock_parse_dir, fake_repo):
    """Ensure analyzer handles chunk writing failures gracefully."""
    with pytest.raises(Exception):
        analyze_repo(str(fake_repo))


def test_analyze_repo_output_json(tmp_path):
    """Integration-style test: create an output JSONL file and verify it's written."""
    output_path = tmp_path / "chunks.jsonl"

    # Mock dependencies
    with patch("analyzer.parse_directory") as mock_parse_dir, \
         patch("analyzer.write_chunks_json") as mock_write_chunks:
        mock_parse_dir.return_value = {
            "total_files": 1,
            "binary_files": [],
            "text_files": [str(tmp_path / "file1.py")]
        }
        mock_write_chunks.return_value = 1

        summary, chunks_written = analyze_repo(str(tmp_path), out_json=str(output_path))
        assert chunks_written == 1
        assert summary["total_files"] == 1


def test_analyze_repo_empty_dir(tmp_path):
    """Handles empty directory correctly."""
    os.makedirs(tmp_path, exist_ok=True)

    with patch("analyzer.parse_directory", return_value={
        "total_files": 0, "binary_files": [], "text_files": []
    }) as mock_parse_dir, \
         patch("analyzer.write_chunks_json", return_value=0) as mock_write_chunks:
        summary, chunks_written = analyze_repo(str(tmp_path))

        assert summary["total_files"] == 0
        assert chunks_written == 0
        mock_parse_dir.assert_called_once()
        mock_write_chunks.assert_called_once()
