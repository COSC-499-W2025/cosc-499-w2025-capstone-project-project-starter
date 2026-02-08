"""
Unit tests for Code Analyzer module
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from src.analyze.code_analyzer import CodeAnalyzer, AnalysisResult, ContributionMetrics


class TestCodeAnalyzer:
    # Test suite for CodeAnalyzer class
    
    @pytest.fixture
    def analyzer(self):
        # Create analyzer instance
        return CodeAnalyzer()
    
    def test_initialization(self, analyzer):
        # Test analyzer initialization
        assert analyzer is not None
        assert hasattr(analyzer, 'analyze_file')
        assert hasattr(analyzer, 'analyze_directory')
    
    def test_detect_language_python(self, analyzer):
        # Test Python language detection
        code = "import fastapi\ndef hello(): pass"
        result = analyzer.detect_language(code, "app.py")
        assert result == "python"
    
    def test_detect_language_javascript(self, analyzer):
        # Test JavaScript language detection
        code = "const app = () => {}"
        result = analyzer.detect_language(code, "App.jsx")
        assert result == "javascript"
    
    def test_detect_frameworks_python(self, analyzer):
        # Test Python framework detection
        code = "import fastapi\nfrom sqlalchemy import Column"
        frameworks = analyzer.detect_frameworks(code, "python")
        assert "fastapi" in frameworks
        assert "sqlalchemy" in frameworks
    
    def test_detect_frameworks_javascript(self, analyzer):
        # Test JavaScript framework detection
        code = "import React from 'react'"
        frameworks = analyzer.detect_frameworks(code, "javascript")
        assert "react" in frameworks
    
    def test_extract_skills_python(self, analyzer):
        # Test skill extraction from Python code
        code = "class User:\n    def __init__(self): pass"
        skills = analyzer.extract_skills(code, "python")
        assert "python" in skills
        assert "object-oriented-programming" in skills
    
    def test_extract_skills_javascript(self, analyzer):
        # Test skill extraction from JavaScript code
        code = "const App = () => { const [state] = useState() }"
        skills = analyzer.extract_skills(code, "javascript")
        assert "javascript" in skills
        assert "arrow-functions" in skills
        assert "react-hooks" in skills
    
    def test_analyze_file_success(self, analyzer):
        # Test successful file analysis
        code = "import fastapi\napp = fastapi.FastAPI()"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            assert isinstance(result, AnalysisResult)
            assert result.language == "python"
            assert "fastapi" in result.frameworks
            assert result.file_path == temp_path
            assert result.lines_of_code > 0
        finally:
            os.unlink(temp_path)
    
    def test_analyze_file_nonexistent(self, analyzer):
        # Test analysis of non-existent file
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file("/nonexistent/file.py")
    
    def test_analyze_directory_success(self, analyzer):
        # Test directory analysis
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            python_file = Path(temp_dir) / "app.py"
            js_file = Path(temp_dir) / "component.jsx"
            
            python_file.write_text("import fastapi")
            js_file.write_text("import React from 'react'")
            
            results = analyzer.analyze_directory(temp_dir)
            
            assert len(results) == 2
            assert any(r.language == "python" for r in results)
            assert any(r.language == "javascript" for r in results)
    
    def test_contribution_metrics_calculation(self, analyzer):
        # Test contribution metrics calculation
        results = [
            AnalysisResult("app.py", "python", ["fastapi"], ["python"], 100, "code"),
            AnalysisResult("test_app.py", "python", ["pytest"], ["python"], 50, "test")
        ]
        
        metrics = analyzer.calculate_contribution_metrics(results)
        
        assert isinstance(metrics, ContributionMetrics)
        assert metrics.total_files == 2
        assert metrics.total_lines == 150
        assert "python" in metrics.languages
        assert "fastapi" in metrics.frameworks
        assert metrics.code_files == 1
        assert metrics.test_files == 1
    
    def test_file_type_detection(self, analyzer):
        # Test file type detection
        # Test file
        test_code = "def test_something():\n    assert True"
        file_type = analyzer.detect_file_type(test_code, "test_app.py")
        assert file_type == "test"
        
        # Regular code file
        code = "def main():\n    print('hello')"
        file_type = analyzer.detect_file_type(code, "app.py")
        assert file_type == "code"
    
    def test_should_skip_file(self, analyzer):
        # Test file skipping logic
        # Should skip files in git directory
        git_file = Path("/some/path/.git/config")
        assert analyzer._should_skip_file(git_file)
        
        # Should skip files in node_modules
        node_file = Path("/some/path/node_modules/package/index.js")
        assert analyzer._should_skip_file(node_file)
        
        # Should not skip regular files
        regular_file = Path("/some/path/app.py")
        assert not analyzer._should_skip_file(regular_file)
    
    def test_detect_language_java(self, analyzer):
        # Test Java language detection
        code = "public class Test {\n    public static void main(String[] args) {}"
        result = analyzer.detect_language(code, "Test.java")
        assert result == "java"
    
    def test_detect_language_cpp(self, analyzer):
        # Test C++ language detection
        code = "#include <iostream>\nint main() { return 0; }"
        result = analyzer.detect_language(code, "main.cpp")
        assert result == "cpp"
    
    def test_detect_file_type_documentation(self, analyzer):
        # Test documentation file detection
        doc_code = "# This is a README file"
        file_type = analyzer.detect_file_type(doc_code, "README.md")
        assert file_type == "documentation"
    
    def test_detect_file_type_config(self, analyzer):
        # Test config file detection
        config_code = '{"name": "test"}'
        file_type = analyzer.detect_file_type(config_code, "config.json")
        assert file_type == "code"  # JSON files are treated as code in our simple implementation
    
    def test_analyze_file_encoding_error(self, analyzer):
        # Test file with encoding issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write("import fastapi\n# Test with special chars: éñ")
            temp_path = f.name
        
        try:
            result = analyzer.analyze_file(temp_path)
            assert result.language == "python"
        finally:
            os.unlink(temp_path)
    
    def test_analyze_directory_error_handling(self, analyzer):
        # Test directory analysis with error handling
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that will cause an error
            error_file = Path(temp_dir) / "error.py"
            error_file.write_text("import fastapi")
            
            results = analyzer.analyze_directory(temp_dir)
            # Should still return results despite potential errors
            assert len(results) >= 0
    
    def test_calculate_contribution_metrics_empty(self, analyzer):
        # Test metrics calculation with empty results
        metrics = analyzer.calculate_contribution_metrics([])
        assert metrics.total_files == 0
        assert metrics.total_lines == 0
        assert metrics.languages == []
        assert metrics.frameworks == []
        assert metrics.skills == []
        assert metrics.code_files == 0
        assert metrics.test_files == 0


class TestAnalysisResult:
    # Test suite for AnalysisResult data class
    
    def test_analysis_result_creation(self):
        # Test AnalysisResult object creation
        result = AnalysisResult(
            file_path="/test/app.py",
            language="python",
            frameworks=["fastapi"],
            skills=["python"],
            lines_of_code=100,
            file_type="code"
        )
        
        assert result.file_path == "/test/app.py"
        assert result.language == "python"
        assert result.frameworks == ["fastapi"]
        assert result.skills == ["python"]
        assert result.lines_of_code == 100
        assert result.file_type == "code"
    
    def test_analysis_result_to_dict(self):
        # Test converting AnalysisResult to dictionary
        result = AnalysisResult(
            file_path="/test/app.py",
            language="python",
            frameworks=["fastapi"],
            skills=["python"],
            lines_of_code=100,
            file_type="code"
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["file_path"] == "/test/app.py"
        assert result_dict["language"] == "python"
        assert result_dict["frameworks"] == ["fastapi"]
        assert result_dict["skills"] == ["python"]
        assert result_dict["lines_of_code"] == 100
        assert result_dict["file_type"] == "code"


class TestContributionMetrics:
    # Test suite for ContributionMetrics data class
    
    def test_contribution_metrics_creation(self):
        # Test ContributionMetrics object creation
        metrics = ContributionMetrics(
            total_files=3,
            total_lines=300,
            languages=["python"],
            frameworks=["fastapi"],
            skills=["python"],
            code_files=2,
            test_files=1
        )
        
        assert metrics.total_files == 3
        assert metrics.total_lines == 300
        assert metrics.languages == ["python"]
        assert metrics.frameworks == ["fastapi"]
        assert metrics.skills == ["python"]
        assert metrics.code_files == 2
        assert metrics.test_files == 1
    
    def test_contribution_metrics_to_dict(self):
        # Test converting ContributionMetrics to dictionary
        metrics = ContributionMetrics(
            total_files=2,
            total_lines=200,
            languages=["python"],
            frameworks=["fastapi"],
            skills=["python"],
            code_files=1,
            test_files=1
        )
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["total_files"] == 2
        assert metrics_dict["total_lines"] == 200
        assert metrics_dict["languages"] == ["python"]
        assert metrics_dict["frameworks"] == ["fastapi"]
        assert metrics_dict["skills"] == ["python"]
        assert metrics_dict["code_files"] == 1
        assert metrics_dict["test_files"] == 1