"""
Comprehensive test suite for the Pipeline Orchestrator
Tests ZIP parsing, categorization, and orchestrator integration
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import zipfile
import json
from src.pipeline.orchestrator import ArtifactPipeline


@pytest.fixture
def test_project_dir(tmp_path):
    """
    Create a temporary test project with various file types
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create code files
    (project_dir / "src").mkdir()
    (project_dir / "src" / "main.py").write_text("""
def hello_world():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
""")
    
    (project_dir / "src" / "utils.js").write_text("""
function greet(name) {
    console.log(`Hello, ${name}!`);
}

module.exports = { greet };
""")
    
    (project_dir / "src" / "config.json").write_text("""
{
    "app_name": "Test App",
    "version": "1.0.0"
}
""")
    
    # Create documentation files
    (project_dir / "README.md").write_text("""
# Test Project

This is a test project for the orchestrator.

## Features
- Feature 1
- Feature 2
""")
    
    (project_dir / "docs").mkdir()
    (project_dir / "docs" / "guide.txt").write_text("""
User Guide

This is a simple user guide for the test application.
It contains multiple lines of documentation.
""")
    
    # Create image files (empty placeholders)
    (project_dir / "assets").mkdir()
    (project_dir / "assets" / "logo.png").write_bytes(b"fake png data")
    (project_dir / "assets" / "banner.jpg").write_bytes(b"fake jpg data")
    
    # Create other files
    (project_dir / "data.csv").write_text("name,age\nJohn,30\nJane,25\n")
    (project_dir / ".gitignore").write_text("*.pyc\n__pycache__/\n")
    
    return project_dir


@pytest.fixture
def test_zip_file(test_project_dir, tmp_path):
    """
    Create a ZIP file from the test project
    """
    zip_path = tmp_path / "test_project.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in test_project_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(test_project_dir.parent)
                zipf.write(file_path, arcname)
    
    return zip_path


@pytest.fixture
def pipeline():
    """Create a pipeline instance"""
    return ArtifactPipeline()


class TestOrchestratorBasics:
    """Test basic orchestrator functionality"""
    
    def test_pipeline_initialization(self, pipeline):
        """Test that pipeline initializes correctly"""
        assert pipeline is not None
        assert isinstance(pipeline, ArtifactPipeline)
    
    def test_start_with_valid_zip(self, pipeline, test_zip_file):
        """Test that start() works with a valid ZIP file"""
        result = pipeline.start(str(test_zip_file))
        
        assert result is not None
        assert isinstance(result, dict)
        assert 'zip_metadata' in result
        assert 'file_info' in result
        assert 'categorized_contents' in result
    
    def test_start_with_nonexistent_zip(self, pipeline):
        """Test that start() raises error for non-existent ZIP"""
        with pytest.raises(FileNotFoundError):
            pipeline.start('/path/to/nonexistent.zip')
    
    def test_start_with_non_zip_file(self, pipeline, tmp_path):
        """Test that start() raises error for non-ZIP file"""
        txt_file = tmp_path / "not_a_zip.txt"
        txt_file.write_text("This is not a ZIP file")
        
        with pytest.raises(ValueError, match="must be a ZIP archive"):
            pipeline.start(str(txt_file))


class TestZipMetadata:
    """Test ZIP metadata extraction"""
    
    def test_zip_metadata_structure(self, pipeline, test_zip_file):
        """Test that ZIP metadata has correct structure"""
        result = pipeline.start(str(test_zip_file))
        metadata = result['zip_metadata']
        
        assert 'root_name' in metadata
        assert 'file_count' in metadata
        assert 'total_uncompressed_bytes' in metadata
        assert 'total_compressed_bytes' in metadata
    
    def test_zip_metadata_values(self, pipeline, test_zip_file):
        """Test that ZIP metadata has reasonable values"""
        result = pipeline.start(str(test_zip_file))
        metadata = result['zip_metadata']
        
        assert metadata['file_count'] > 0
        assert metadata['total_uncompressed_bytes'] > 0
        assert metadata['total_compressed_bytes'] >= 0
        assert 'test_project' in metadata['root_name']


class TestFileInfo:
    """Test file info extraction"""
    
    def test_file_info_structure(self, pipeline, test_zip_file):
        """Test that file_info has correct structure"""
        result = pipeline.start(str(test_zip_file))
        file_info = result['file_info']
        
        assert isinstance(file_info, list)
        assert len(file_info) > 0
        
        # Check first file has required fields
        first_file = file_info[0]
        assert 'abs_path' in first_file
        assert 'rel_path' in first_file
        assert 'size' in first_file
        assert 'sha256' in first_file
        assert 'ext' in first_file
    
    def test_file_info_contains_expected_files(self, pipeline, test_zip_file):
        """Test that file_info contains our test files"""
        result = pipeline.start(str(test_zip_file))
        file_info = result['file_info']
        
        rel_paths = [f['rel_path'] for f in file_info]
        
        # Check for some expected files
        assert any('main.py' in path for path in rel_paths)
        assert any('utils.js' in path for path in rel_paths)
        assert any('README.md' in path for path in rel_paths)


class TestCategorization:
    """Test file categorization"""
    
    def test_categorized_contents_structure(self, pipeline, test_zip_file):
        """Test that categorized_contents has correct structure"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        assert isinstance(categorized, dict)
        assert 'code' in categorized
        assert 'code_by_language' in categorized
        assert 'documentation' in categorized
        assert 'images' in categorized
        assert 'sketches' in categorized
        assert 'other' in categorized
    
    def test_code_files_categorized(self, pipeline, test_zip_file):
        """Test that code files are properly categorized"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        code_files = categorized['code']
        assert len(code_files) > 0
        
        # Check that our Python and JS files are in code
        assert any('main.py' in f for f in code_files)
        assert any('utils.js' in f for f in code_files)
    
    def test_code_by_language(self, pipeline, test_zip_file):
        """Test that code files are grouped by language"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        code_by_lang = categorized['code_by_language']
        assert isinstance(code_by_lang, dict)
        
        # Should have Python and JavaScript
        assert 'python' in code_by_lang
        assert 'javascript' in code_by_lang
        
        # Check files are in correct language groups
        python_files = code_by_lang['python']
        js_files = code_by_lang['javascript']
        
        assert any('main.py' in f for f in python_files)
        assert any('utils.js' in f for f in js_files)
    
    def test_documentation_categorized(self, pipeline, test_zip_file):
        """Test that documentation files are properly categorized"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        doc_files = categorized['documentation']
        assert len(doc_files) > 0
        
        # Check that README and guide are in documentation
        assert any('README.md' in f for f in doc_files)
        assert any('guide.txt' in f for f in doc_files)
    
    def test_images_categorized(self, pipeline, test_zip_file):
        """Test that image files are properly categorized"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        image_files = categorized['images']
        assert len(image_files) > 0
        
        # Check that our image files are categorized
        assert any('logo.png' in f for f in image_files)
        assert any('banner.jpg' in f for f in image_files)
    
    def test_other_files_categorized(self, pipeline, test_zip_file):
        """Test that uncategorized files go to 'other'"""
        result = pipeline.start(str(test_zip_file))
        categorized = result['categorized_contents']
        
        other_files = categorized['other']
        
        # CSV should be in other
        assert any('data.csv' in f for f in other_files)
        
        # JSON is actually categorized as code (language: json)
        # So config.json should be in code, not other
        code_files = categorized['code']
        assert any('config.json' in f for f in code_files)
        
        # Verify it's in the json language group
        json_files = categorized['code_by_language'].get('json', [])
        assert any('config.json' in f for f in json_files)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_zip(self, pipeline, tmp_path):
        """Test handling of empty ZIP file"""
        empty_zip = tmp_path / "empty.zip"
        with zipfile.ZipFile(empty_zip, 'w'):
            pass  # Create empty ZIP
        
        result = pipeline.start(str(empty_zip))
        
        # Should still return valid structure
        assert 'categorized_contents' in result
        categorized = result['categorized_contents']
        
        # All categories should be empty
        assert len(categorized['code']) == 0
        assert len(categorized['documentation']) == 0
        assert len(categorized['images']) == 0
    
    def test_zip_with_nested_directories(self, pipeline, tmp_path):
        """Test ZIP with deeply nested directory structure"""
        nested_dir = tmp_path / "nested"
        nested_dir.mkdir()
        
        # Create deeply nested structure
        deep_path = nested_dir / "level1" / "level2" / "level3"
        deep_path.mkdir(parents=True)
        (deep_path / "deep_file.py").write_text("print('deep')")
        
        # Create ZIP
        zip_path = tmp_path / "nested.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in nested_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(nested_dir.parent)
                    zipf.write(file_path, arcname)
        
        result = pipeline.start(str(zip_path))
        categorized = result['categorized_contents']
        
        # Should find the deeply nested Python file
        assert len(categorized['code']) > 0
        assert any('deep_file.py' in f for f in categorized['code'])
    
    def test_zip_with_windows_style_backslash_paths(self, pipeline, tmp_path):
        """
        Test ZIP file with Windows-style backslash paths (regression test)
        
        This tests the fix for issue where ZIP files created on Windows
        with backslash separators were not being extracted properly,
        causing all files to appear as flat file names instead of
        creating proper directory structures.
        """
        # Create a ZIP file with Windows-style paths manually
        zip_path = tmp_path / "windows_paths.zip"
        
        # Create multiple projects with backslash paths
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Create a multi-project structure with Windows paths
            zipf.writestr('project-a\\README.md', '# Project A')
            zipf.writestr('project-a\\src\\main.py', 'print("A")')
            zipf.writestr('project-b\\README.md', '# Project B')
            zipf.writestr('project-b\\src\\app.js', 'console.log("B");')
            zipf.writestr('README.md', '# Root README')
        
        result = pipeline.start(str(zip_path))
        
        # Verify that project ranking was generated with multiple projects
        assert 'project_ranking' in result
        project_ranking = result['project_ranking']
        
        # Should detect 2 separate projects, not treat everything as flat files
        assert 'ranked_projects' in project_ranking
        assert len(project_ranking['ranked_projects']) == 2, "Should detect 2 separate projects"
        
        # Verify project names from summaries
        assert 'top_summaries' in project_ranking
        project_names = {proj['name'] for proj in project_ranking['top_summaries']}
        assert 'project-a' in project_names
        assert 'project-b' in project_names
        
        # Verify the projects have proper directory structure (not flat files)
        code_files = result['categorized_contents']['code']
        doc_files = result['categorized_contents']['documentation']
        
        # Files should have proper paths with forward slashes (normalized)
        assert any('project-a/src/main.py' in f for f in code_files)
        assert any('project-b/src/app.js' in f for f in code_files)
        assert any('project-a/README.md' in f for f in doc_files)
        assert any('project-b/README.md' in f for f in doc_files)


class TestIntegration:
    """Integration tests for full pipeline"""
    
    def test_full_pipeline_execution(self, pipeline, test_zip_file):
        """Test complete pipeline execution from start to finish"""
        result = pipeline.start(str(test_zip_file))
        
        # Verify all major components are present
        assert result['zip_metadata']['file_count'] > 0
        assert len(result['file_info']) > 0
        assert len(result['categorized_contents']['code']) > 0
        assert len(result['categorized_contents']['documentation']) > 0
        assert len(result['categorized_contents']['images']) > 0
    
    def test_result_is_json_serializable(self, pipeline, test_zip_file):
        """Test that result can be serialized to JSON"""
        result = pipeline.start(str(test_zip_file))
        
        # Should be able to convert to JSON without errors
        json_str = json.dumps(result)
        assert json_str is not None
        
        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed['zip_metadata'] == result['zip_metadata']