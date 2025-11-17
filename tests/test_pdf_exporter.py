import sys
import os
import pytest

# Add src folder to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from exporter.pdf_exporter import export

@pytest.fixture
def tmp_pdf(tmp_path):
    return tmp_path / "test_report.pdf"

def test_pdf_export_creates_file(tmp_pdf):
    """Normal export with valid predictions."""
    mock_data = {
        "predictions": [
            ["Flask", 0.93],
            ["SQL", 0.71],
            ["React", 0.62]
        ]
    }
    export(mock_data, filename=str(tmp_pdf))
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0

def test_pdf_export_empty_predictions(tmp_pdf):
    """Export with empty predictions list."""
    mock_data = {"predictions": []}
    export(mock_data, filename=str(tmp_pdf))
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0

def test_pdf_export_missing_predictions_key(tmp_pdf):
    """Export with dict missing 'predictions' key."""
    mock_data = {"skills": [["Flask", 0.9]]}  # wrong key
    export(mock_data, filename=str(tmp_pdf))
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0

def test_pdf_export_invalid_type(tmp_pdf):
    """Export with completely invalid type (not a dict)."""
    mock_data = ["Flask", "SQL"]  # should be dict
    # The function should handle this gracefully
    export(mock_data, filename=str(tmp_pdf))
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0

def test_pdf_export_predictions_not_list(tmp_pdf):
    """Export where 'predictions' key exists but is not a list."""
    mock_data = {"predictions": "not a list"}
    export(mock_data, filename=str(tmp_pdf))
    assert tmp_pdf.exists()
    assert tmp_pdf.stat().st_size > 0
