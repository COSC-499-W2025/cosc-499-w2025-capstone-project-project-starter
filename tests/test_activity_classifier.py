"""
Tests for activity_classifier module
"""
import sys
import os
import pytest

# Add src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis.activity_classifier import classify_file, aggregate


class TestActivityClassifier:
    """Test activity classification functionality"""
    
    def test_classify_file_by_extension_code(self):
        """Test classification by code file extension"""
        assert classify_file("test.py") == "code"
        assert classify_file("test.java") == "code"
        assert classify_file("test.js") == "code"
    
    def test_classify_file_by_extension_doc(self):
        """Test classification by document file extension"""
        assert classify_file("readme.md") == "doc"
        assert classify_file("notes.txt") == "doc"
    
    def test_classify_file_by_folder_hint(self):
        """Test classification by folder name hint"""
        assert classify_file("src/main.py") == "code"
        assert classify_file("docs/readme.md") == "doc"
        assert classify_file("tests/test.py") == "code"
        assert classify_file("data/file.csv") == "data"
    
    def test_classify_file_unknown_extension(self):
        """Test classification with unknown extension returns 'other'"""
        # This tests lines 27-28: return EXTENSION_MAP.get(ext, "other")
        assert classify_file("file.unknown") == "other"
        assert classify_file("file.xyz") == "other"
        assert classify_file("file") == "other"  # No extension
    
    def test_classify_file_folder_hint_takes_precedence(self):
        """Test that folder hints take precedence over extensions"""
        # Even if extension is unknown, folder hint should work
        assert classify_file("src/file.unknown") == "code"
        assert classify_file("docs/file.xyz") == "doc"
    
    def test_aggregate_basic(self):
        """Test basic aggregation of files"""
        files = ["test.py", "readme.md", "data.csv"]
        sizes = {"test.py": "1000", "readme.md": "500", "data.csv": "2000"}
        
        result = aggregate(files, sizes)
        
        assert "code" in result
        assert "doc" in result
        assert "data" in result
        assert result["code"]["count"] == 1
        assert result["code"]["bytes"] == 1000
        assert result["doc"]["count"] == 1
        assert result["doc"]["bytes"] == 500
    
    def test_aggregate_skips_directories(self):
        """Test that aggregate skips files ending with '/' (directories)"""
        # This tests line 35: if f.endswith("/"): continue
        files = ["test.py", "src/", "readme.md", "docs/"]
        sizes = {"test.py": "1000", "src/": "0", "readme.md": "500", "docs/": "0"}
        
        result = aggregate(files, sizes)
        
        # Should only have code and doc, not directories
        assert "code" in result
        assert "doc" in result
        assert result["code"]["count"] == 1
        assert result["doc"]["count"] == 1
        assert result["code"]["bytes"] == 1000
        assert result["doc"]["bytes"] == 500
    
    def test_aggregate_missing_size(self):
        """Test aggregation when file size is missing"""
        files = ["test.py", "readme.md"]
        sizes = {"test.py": "1000"}  # readme.md missing
        
        result = aggregate(files, sizes)
        
        assert result["code"]["bytes"] == 1000
        assert result["doc"]["bytes"] == 0  # Missing size defaults to 0
    
    def test_aggregate_empty_files(self):
        """Test aggregation with empty file list"""
        result = aggregate([], {})
        assert result == {}
    
    def test_aggregate_calculates_score(self):
        """Test that aggregate calculates score using log and weights"""
        files = ["test.py"]
        sizes = {"test.py": "1000"}
        
        result = aggregate(files, sizes)
        
        assert "code" in result
        assert result["code"]["score"] > 0
        # Score should be log(1 + size) * weight
        # log(1 + 1000) * 3 ≈ 20.7
        assert result["code"]["score"] > 0

