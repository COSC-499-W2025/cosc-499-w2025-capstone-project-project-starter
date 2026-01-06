import tempfile
from pathlib import Path

from codeparser.metrics import (
    classify_file,
    compute_project_duration,
    compute_activity_frequencies,
    extract_metrics,
)


# -------------------------------
# Helper
# -------------------------------
def create_temp_project(files):
    """
    Create a temporary directory containing a structure of files.
    `files` is a dict: { "path/filename.ext": "file content" }
    """
    temp_dir = tempfile.mkdtemp()
    base = Path(temp_dir)

    for rel, content in files.items():
        file_path = base / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    return temp_dir


# -------------------------------
# classify_file tests
# -------------------------------
def test_classify_code_files():
    assert classify_file("main.py") == "code"
    assert classify_file("script.js") == "code"
    assert classify_file("module.cpp") == "code"


def test_classify_test_files():
    assert classify_file("test_utils.py") == "test"
    assert classify_file("tests/test_something.py") == "test"


def test_classify_document_files():
    assert classify_file("README.md") == "document"
    assert classify_file("notes.txt") == "document"


def test_classify_design_files():
    assert classify_file("diagram.drawio") == "design"
    assert classify_file("image.png") == "design"


def test_classify_other_files():
    assert classify_file("archive.bin") == "other"
    assert classify_file("unknown.xyz") == "other"


# -------------------------------
# project duration tests
# -------------------------------
def test_compute_project_duration_valid():
    temp_project = create_temp_project({
        "src/a.py": "print('hi')",
        "docs/readme.md": "hello",
    })

    duration = compute_project_duration(temp_project)

    assert "start" in duration
    assert "end" in duration
    assert "duration_days" in duration
    assert duration["duration_days"] >= 0


# -------------------------------
# activity frequencies tests
# -------------------------------
def test_compute_activity_frequencies_counts_correctly():
    temp_project = create_temp_project({
        "src/code.py": "print('hi')",
        "tests/test_file.py": "assert True",
        "docs/readme.md": "hello",
        "design/diagram.drawio": "<xml>",
        "data.bin": "001101",
    })

    freq = compute_activity_frequencies(temp_project)

    assert freq["code"] == 1
    assert freq["test"] == 1
    assert freq["document"] == 1
    assert freq["design"] == 1
    assert freq["other"] == 1


# -------------------------------
# extract_metrics integration test
# -------------------------------
def test_extract_metrics_integration():
    temp_project = create_temp_project({
        "src/app.py": "print('hello')",
        "docs/info.txt": "info",
        "test/test_app.py": "assert True",
    })

    metrics = extract_metrics(temp_project)

    # basic structure
    assert "project_duration" in metrics
    assert "activity_frequencies" in metrics
    assert "total_files" in metrics

    # check correct totals
    freq = metrics["activity_frequencies"]
    assert freq["code"] == 1
    assert freq["document"] == 1
    assert freq["test"] == 1

    assert metrics["total_files"] == 3
