"""
test_file_categorizer.py
------------------------
Tests for file_categorizer.py using pytest.
Updated for the flattened categorization output (single-level structure).

Run from root directory with:
    docker compose run --rm backend python3 -m pytest tests/categorize/test_file_categorizer.py -v
    (coverage) docker compose run --rm -e PYTHONPATH=/code backend sh -lc 'coverage run --source=src -m pytest tests/categorize/test_file_categorizer.py && coverage report -m'
"""

import pytest
import tempfile
from pathlib import Path
from src.categorize.file_categorizer import (
    categorize_folder_structure,
    categorize_file,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary folder with a mock project hierarchy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # Folder structure
        (base / "project1").mkdir()
        (base / "project1" / "docs").mkdir()
        (base / "project1" / "images").mkdir()
        (base / "emptydir").mkdir()
        # Code files (multiple languages)
        (base / "project1" / "main.py").write_text("print('hello')")
        (base / "project1" / "helper.cpp").write_text("int main(){}")
        (base / "project1" / "App.java").write_text("class App {}")
        (base / "project1" / "script.sh").write_text("echo hi")
        # Non-code files
        (base / "project1" / "README.md").write_text("# Readme")
        (base / "project1" / "docs" / "design.pdf").write_text("pdf data")
        (base / "project1" / "images" / "diagram.png").write_bytes(b"imagebytes")
        (base / "notes.txt").write_text("root note")

        yield base


def test_categorize_file_by_extension():
    """Verify correct category is assigned based on file extension."""
    assert categorize_file("script.py") == "code"
    assert categorize_file("notes.txt") == "documentation"
    assert categorize_file("diagram.png") == "images"
    assert categorize_file("design.drawio") == "sketches"
    assert categorize_file("random.bin") == "other"


def test_flattened_structure_keys_and_categories(temp_project_dir):
    """Ensure flattened structure contains correct global categories and language breakdown."""
    result = categorize_folder_structure(temp_project_dir)

    # --- Core keys must exist ---
    for key in ["code", "documentation", "images", "sketches", "other", "code_by_language"]:
        assert key in result

    # --- Validate file presence in correct categories ---
    # Code files
    code_files = result["code"]
    assert any("main.py" in f for f in code_files)
    assert any("helper.cpp" in f for f in code_files)
    assert any("App.java" in f for f in code_files)
    assert any("script.sh" in f for f in code_files)

    # Documentation
    docs = result["documentation"]
    assert any("README.md" in f for f in docs)
    assert any("design.pdf" in f for f in docs)
    assert any("notes.txt" in f for f in docs)

    # Images
    imgs = result["images"]
    assert any("diagram.png" in f for f in imgs)

    # --- Check language mapping ---
    langs = result["code_by_language"]
    for expected_lang in ["python", "cpp", "java", "shell"]:
        assert expected_lang in langs

    # Confirm specific files per language
    assert any("main.py" in f for f in langs["python"])
    assert any("helper.cpp" in f for f in langs["cpp"])
    assert any("App.java" in f for f in langs["java"])
    assert any("script.sh" in f for f in langs["shell"])


def test_invalid_path_raises_valueerror():
    """Invalid folder path should raise ValueError."""
    with pytest.raises(ValueError):
        categorize_folder_structure("/non/existent/path")


def test_empty_directory_returns_empty_categories(temp_project_dir):
    """Empty directory should still produce empty category lists and dicts."""
    # Create an empty folder for this test
    empty_dir = temp_project_dir / "completely_empty"
    empty_dir.mkdir()

    result = categorize_folder_structure(empty_dir)

    for key in ["code", "documentation", "images", "sketches", "other", "code_by_language"]:
        assert key in result
        if key == "code_by_language":
            assert isinstance(result[key], dict)
            assert result[key] == {}
        else:
            assert result[key] == []