import sys
import os
import pytest

# Add src folder to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from src.exporter.pdf_exporter import export, collect_predictions


@pytest.fixture
def tmp_pdf(tmp_path):
    return tmp_path / "test_report.pdf"


# --- Tests for export() ---

def test_pdf_export_creates_file(tmp_pdf):
    """Normal export with valid predictions."""
    mock_data = {
        "predictions": [
            ["Flask", 0.93],
            ["SQL", 0.71],
            ["React", 0.62]
        ]
    }
    export(mock_data, filename=str(tmp_pdf), consent="y")
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0


def test_pdf_export_empty_predictions(tmp_pdf):
    """Export with empty predictions list."""
    mock_data = {"predictions": []}
    export(mock_data, filename=str(tmp_pdf), consent="y")
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0


def test_pdf_export_missing_predictions_key(tmp_pdf):
    """Export with dict missing 'predictions' key."""
    mock_data = {"skills": [["Flask", 0.9]]}  # wrong key
    export(mock_data, filename=str(tmp_pdf), consent="y")
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0


def test_pdf_export_invalid_type(tmp_pdf):
    """Export with completely invalid type (not a dict)."""
    mock_data = ["Flask", "SQL"]  # should be dict
    export(mock_data, filename=str(tmp_pdf), consent="y")
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0


def test_pdf_export_predictions_not_list(tmp_pdf):
    """Export where 'predictions' key exists but is not a list."""
    mock_data = {"predictions": "not a list"}
    export(mock_data, filename=str(tmp_pdf), consent="y")
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0


# --- Tests for collect_predictions() ---

def test_collect_predictions_basic():
    parsed = [
        {"file": "a.txt", "skills": [["Python", 0.9]]},
        {"file": "b.txt", "skills": [["SQL", 0.8]]},
    ]
    result = collect_predictions(parsed)
    assert result == [
        ["a.txt: Python", 0.9],
        ["b.txt: SQL", 0.8],
    ]


def test_collect_predictions_uses_predictions_key():
    parsed = [
        {"file": "code.py", "predictions": [["Flask", 0.7]]}
    ]
    result = collect_predictions(parsed)
    assert result == [["code.py: Flask", 0.7]]


def test_collect_predictions_skips_invalid_entries():
    parsed = [
        {
            "file": "bad.json",
            "skills": [
                ["Valid", 0.99],
                ["MissingProb"],
                ["Too", "Many", "Values"],
                "not even a list",
            ]
        }
    ]
    result = collect_predictions(parsed)
    assert result == [["bad.json: Valid", 0.99]]


def test_collect_predictions_non_list_skills():
    parsed = [{"file": "test", "skills": "not a list"}]
    result = collect_predictions(parsed)
    assert result == []


def test_collect_predictions_non_list_folder():
    parsed = {"not": "a list"}
    result = collect_predictions(parsed)
    assert result == []


def test_collect_predictions_missing_filename():
    parsed = [{"skills": [["C++", 0.55]]}]
    result = collect_predictions(parsed)
    assert result == [["Unknown file: C++", 0.55]]

def test_pdf_export_with_llm_section_increases_size(tmp_path):
    pdf_no_llm = tmp_path / "no_llm.pdf"
    pdf_with_llm = tmp_path / "with_llm.pdf"

    mock_data = {
        "predictions": [
            ["Flask", 0.93],
            ["SQL", 0.71],
        ]
    }

    # Export without LLM
    export(mock_data, filename=str(pdf_no_llm))
    size_without = pdf_no_llm.stat().st_size

    # Export with LLM
    llm_text = "This is an LLM analysis.\nIt has multiple lines.\nIt should appear as a section."
    export(mock_data, llm_response=llm_text, filename=str(pdf_with_llm))
    size_with = pdf_with_llm.stat().st_size

    assert pdf_with_llm.exists()
    assert size_with > size_without     # PDF must be larger when LLM content is included

def test_pdf_export_empty_llm_same_as_no_llm(tmp_path):
    pdf_no_llm = tmp_path / "no_llm2.pdf"
    pdf_empty_llm = tmp_path / "empty_llm.pdf"

    mock_data = {"predictions": [["Python", 0.95]]}

    export(mock_data, filename=str(pdf_no_llm))
    export(mock_data, llm_response="", filename=str(pdf_empty_llm))

    size_no_llm = pdf_no_llm.stat().st_size
    size_empty_llm = pdf_empty_llm.stat().st_size

    # Sizes won't be byte-for-byte identical, but they should be close enough
    assert abs(size_no_llm - size_empty_llm) < 50

def test_pdf_export_llm_none_same_as_omitted(tmp_path):
    pdf_default = tmp_path / "default_llm.pdf"
    pdf_none = tmp_path / "none_llm.pdf"

    mock_data = {"predictions": [["JavaScript", 0.8]]}

    export(mock_data, filename=str(pdf_default))
    export(mock_data, llm_response=None, filename=str(pdf_none))

    size_default = pdf_default.stat().st_size
    size_none = pdf_none.stat().st_size

    assert abs(size_default - size_none) < 50
