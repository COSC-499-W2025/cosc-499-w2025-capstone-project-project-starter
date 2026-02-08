"""
Test suite for JSON report generation in the Pipeline Orchestrator
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import zipfile
import json
import shutil
from src.pipeline.orchestrator import ArtifactPipeline


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a simple test project"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create a simple Python file
    (project_dir / "main.py").write_text("""
def hello():
    print("Hello, World!")
""")
    
    # Create a README
    (project_dir / "README.md").write_text("""
# Test Project
This is a test project.
""")
    
    return project_dir


@pytest.fixture
def test_zip_file(test_project_dir, tmp_path):
    """Create a ZIP file from the test project"""
    zip_path = tmp_path / "test_project.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in test_project_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(test_project_dir.parent)
                zipf.write(file_path, arcname)
    
    return zip_path


@pytest.fixture(autouse=True)
def cleanup_reports():
    """Clean up reports directory after each test"""
    yield
    reports_dir = Path("reports")
    if reports_dir.exists():
        for file in reports_dir.glob("report_*.json"):
            file.unlink()


def test_json_report_is_created(test_zip_file):
    """Test that a JSON report file is created in the reports/ directory"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Check that reports directory exists
    reports_dir = Path("reports")
    assert reports_dir.exists(), "reports/ directory should be created"
    
    # Check that at least one report file exists
    report_files = list(reports_dir.glob("report_*.json"))
    assert len(report_files) > 0, "At least one report file should be created"
    
    # Check that the most recent report exists and is readable
    report_file = sorted(report_files)[-1]
    assert report_file.exists(), f"Report file {report_file} should exist"


def test_json_report_is_valid_json(test_zip_file):
    """Test that the generated report is valid JSON"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Try to load the JSON
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Verify it's a dictionary
    assert isinstance(report_data, dict), "Report should be a dictionary"


def test_json_report_has_required_structure(test_zip_file):
    """Test that the JSON report has the expected structure"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Load the JSON
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Check for required top-level keys
    assert "zip_metadata" in report_data, "Report should have zip_metadata"
    assert "projects" in report_data, "Report should have projects"
    
    # Check zip_metadata structure
    zip_meta = report_data["zip_metadata"]
    assert "file_count" in zip_meta, "zip_metadata should have file_count"
    assert "total_uncompressed_bytes" in zip_meta, "zip_metadata should have total_uncompressed_bytes"
    
    # Check projects structure
    projects = report_data["projects"]
    assert isinstance(projects, dict), "projects should be a dictionary"


def test_json_report_organizes_by_project(test_zip_file):
    """Test that the JSON report organizes results by project"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Load the JSON
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Check that projects are organized properly
    projects = report_data["projects"]
    
    for project_name, project_data in projects.items():
        # Each project should have these keys
        assert "categorized_contents" in project_data, f"Project {project_name} should have categorized_contents"
        assert "analysis_results" in project_data, f"Project {project_name} should have analysis_results"
        
        # Check categorized_contents structure
        categorized = project_data["categorized_contents"]
        assert isinstance(categorized, dict), "categorized_contents should be a dictionary"
        
        # Check analysis_results structure
        analysis = project_data["analysis_results"]
        assert isinstance(analysis, dict), "analysis_results should be a dictionary"


def test_json_report_organizes_by_file_type(test_zip_file):
    """Test that the JSON report organizes analysis by file type"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Load the JSON
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Get the first project
    projects = report_data["projects"]
    project_name = list(projects.keys())[0]
    project_data = projects[project_name]
    
    # Check analysis_results has file type organization
    analysis = project_data["analysis_results"]
    
    # Verify file type keys exist (at least some of them)
    possible_keys = ["code", "documentation", "images", "videos"]
    found_keys = [key for key in possible_keys if key in analysis]
    
    assert len(found_keys) > 0, "analysis_results should have at least one file type category"


def test_json_report_filename_format(test_zip_file):
    """Test that the report filename follows the correct format"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Check filename format: report_YYYYMMDD_HHMMSS.json
    filename = report_file.name
    assert filename.startswith("report_"), "Filename should start with 'report_'"
    assert filename.endswith(".json"), "Filename should end with '.json'"
    
    # Extract timestamp part
    timestamp_part = filename[7:-5]  # Remove "report_" and ".json"
    parts = timestamp_part.split("_")
    
    assert len(parts) == 2, "Timestamp should have date and time parts"
    assert len(parts[0]) == 8, "Date part should be YYYYMMDD (8 digits)"
    assert len(parts[1]) == 6, "Time part should be HHMMSS (6 digits)"


def test_json_report_is_serializable(test_zip_file):
    """Test that all data in the report is JSON serializable (no errors)"""
    pipeline = ArtifactPipeline(enable_insights=False)
    
    # Run the pipeline
    result = pipeline.start(str(test_zip_file), use_llm=False)
    
    # Find the most recent report
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("report_*.json"))
    report_file = report_files[-1]
    
    # Load and re-serialize to verify no serialization issues
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Try to serialize it again (should not raise an exception)
    serialized = json.dumps(report_data, indent=2)
    assert len(serialized) > 0, "Report should be serializable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
