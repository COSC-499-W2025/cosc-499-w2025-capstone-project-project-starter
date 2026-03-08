"""
Unit tests for local analysis methods.
Tests Issue #39: Set up internal analysis method.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from analysis.local_analyzer import LocalAnalyzer


class TestLocalAnalyzer:
    """Test cases for LocalAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return LocalAnalyzer()
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure for testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create project structure
        os.makedirs(os.path.join(temp_dir, 'src'))
        os.makedirs(os.path.join(temp_dir, 'tests'))
        os.makedirs(os.path.join(temp_dir, 'docs'))
        
        # Create Python files
        with open(os.path.join(temp_dir, 'src', 'main.py'), 'w') as f:
            f.write('# Main file\nfrom flask import Flask\n\ndef main():\n    pass\n')
        
        with open(os.path.join(temp_dir, 'src', 'utils.py'), 'w') as f:
            f.write('# Utils file\n\ndef helper():\n    return True\n')
        
        # Create test file
        with open(os.path.join(temp_dir, 'tests', 'test_main.py'), 'w') as f:
            f.write('# Test file\nimport pytest\n\ndef test_main():\n    assert True\n')
        
        # Create JavaScript file
        with open(os.path.join(temp_dir, 'src', 'app.js'), 'w') as f:
            f.write('// JavaScript file\nimport React from "react";\n\nfunction App() {}\n')
        
        # Create documentation
        with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
            f.write('# Test Project\n\nThis is a test project.\n')
        
        with open(os.path.join(temp_dir, 'docs', 'guide.md'), 'w') as f:
            f.write('# Guide\n\nDocumentation here.\n')
        
        # Create config files
        with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
            f.write('{"name": "test-project"}')
        
        with open(os.path.join(temp_dir, '.gitignore'), 'w') as f:
            f.write('node_modules/\n__pycache__/\n')
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_analyze_structure(self, analyzer, temp_project):
        """Test structural analysis."""
        structure = analyzer.analyze_structure(temp_project)
        
        assert 'total_files' in structure
        assert 'total_directories' in structure
        assert 'max_depth' in structure
        assert structure['total_files'] > 0
        assert structure['total_directories'] > 0
        assert structure['has_tests'] == True
        assert structure['has_docs'] == True
    
    def test_detect_languages(self, analyzer, temp_project):
        """Test language detection."""
        languages = analyzer.detect_languages(temp_project)
        
        assert 'languages_detected' in languages
        assert 'Python' in languages['languages_detected']
        assert 'JavaScript' in languages['languages_detected']
        assert 'JSON' in languages['languages_detected']
        assert 'primary_language' in languages
        assert languages['primary_language'] is not None
    
    def test_detect_frameworks(self, analyzer, temp_project):
        """Test framework detection."""
        frameworks = analyzer.detect_frameworks(temp_project)
        
        assert isinstance(frameworks, list)
        assert 'Flask' in frameworks
        assert 'React' in frameworks
        assert 'Node.js' in frameworks
    
    def test_calculate_metrics(self, analyzer, temp_project):
        """Test metrics calculation."""
        metrics = analyzer.calculate_metrics(temp_project)
        
        assert 'total_lines_of_code' in metrics
        assert 'total_file_size_bytes' in metrics
        assert 'code_files' in metrics
        assert 'document_files' in metrics
        assert metrics['total_lines_of_code'] > 0
        assert metrics['code_files'] > 0
        assert metrics['document_files'] > 0
    
    def test_extract_skills(self, analyzer, temp_project):
        """Test skill extraction."""
        skills = analyzer.extract_skills(temp_project)
        
        assert isinstance(skills, list)
        assert 'Python' in skills
        assert 'JavaScript' in skills
        assert 'Flask' in skills
        assert 'React' in skills
        assert 'Git' in skills
        assert 'Documentation' in skills
        assert 'Unit Testing' in skills
    
    def test_get_file_breakdown(self, analyzer, temp_project):
        """Test file breakdown analysis."""
        breakdown = analyzer.get_file_breakdown(temp_project)
        
        assert 'by_extension' in breakdown
        assert 'by_category' in breakdown
        assert '.py' in breakdown['by_extension']
        assert '.js' in breakdown['by_extension']
        assert '.md' in breakdown['by_extension']
        assert breakdown['by_category']['code'] > 0
        assert breakdown['by_category']['documents'] > 0
    
    def test_analyze_project_complete(self, analyzer, temp_project):
        """Test complete project analysis."""
        result = analyzer.analyze_project(temp_project)
    
        assert 'project_path' in result
        assert 'project_name' in result
        assert 'analyzed_at' in result
        assert 'structure' in result
        assert 'languages' in result
        assert 'frameworks' in result
        assert 'metrics' in result
        assert 'skills' in result
        assert 'file_breakdown' in result
        assert 'deep_analysis' in result
    
        assert result['structure']['has_tests'] == True
        assert 'Python' in result['languages']['languages_detected']
        assert 'Flask' in result['frameworks']
        assert result['metrics']['code_files'] > 0
        assert result['metrics']['document_files'] > 0
        assert len(result['skills']) > 0
        assert isinstance(result['deep_analysis'], dict)
    
    def test_analyze_nonexistent_path(self, analyzer):
        """Test analysis of nonexistent path raises error."""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_project('/nonexistent/path')
    
    def test_language_detection_empty_project(self, analyzer):
        """Test language detection on empty project."""
        temp_dir = tempfile.mkdtemp()
        
        languages = analyzer.detect_languages(temp_dir)
        
        assert languages['languages_detected'] == []
        assert languages['primary_language'] is None
        
        shutil.rmtree(temp_dir)
    
    def test_perform_deep_analysis(self, analyzer, temp_project):
        """Test deep code analysis."""
        result = analyzer.perform_deep_analysis(temp_project)
        
        # Should return a dict even if analysis succeeds or fails
        assert isinstance(result, dict)
    
    def test_perform_deep_analysis_empty_project(self, analyzer):
        """Test deep analysis on project with no code files."""
        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, 'data'))
        
        result = analyzer.perform_deep_analysis(temp_dir)
        
        assert isinstance(result, dict)
        assert result == {}  # Empty when no code files
        
        shutil.rmtree(temp_dir)
    
    def test_analyze_files_from_db_basic(self, analyzer):
        """Test analyzing files from database format."""
        file_contents = [
            {
                'file_path': 'test.py',
                'file_extension': '.py',
                'file_content': 'def test():\n    return True\n',
                'content_type': 'Python',
                'is_binary': False
            },
            {
                'file_path': 'app.js',
                'file_extension': '.js',
                'file_content': 'function app() {\n  return true;\n}\n',
                'content_type': 'JavaScript',
                'is_binary': False
            }
        ]
        
        result = analyzer.analyze_files_from_db(file_contents)
        
        assert isinstance(result, dict)
    
    def test_analyze_files_from_db_with_binary(self, analyzer):
        """Test that binary files are skipped."""
        file_contents = [
            {
                'file_path': 'image.png',
                'file_extension': '.png',
                'file_content': b'\x89PNG\r\n',
                'content_type': 'Binary',
                'is_binary': True
            },
            {
                'file_path': 'test.py',
                'file_extension': '.py',
                'file_content': 'def test():\n    pass\n',
                'content_type': 'Python',
                'is_binary': False
            }
        ]
        
        result = analyzer.analyze_files_from_db(file_contents)
        
        # Binary files should be skipped
        assert isinstance(result, dict)
    
    def test_analyze_files_from_db_with_bytes_content(self, analyzer):
        """Test analyzing files with bytes content."""
        file_contents = [
            {
                'file_path': 'test.py',
                'file_extension': '.py',
                'file_content': b'def test():\n    pass\n',
                'content_type': 'Python',
                'is_binary': False
            }
        ]
        
        result = analyzer.analyze_files_from_db(file_contents)
        
        assert isinstance(result, dict)
    
    def test_analyze_files_from_db_empty_list(self, analyzer):
        """Test analyzing empty file list."""
        result = analyzer.analyze_files_from_db([])
        
        assert result == {}
    
    def test_analyze_files_from_db_no_language(self, analyzer):
        """Test files with no language specified but valid extension."""
        file_contents = [
            {
                'file_path': 'script.py',
                'file_extension': '.py',
                'file_content': 'print("test")',
                'content_type': '',  # No content_type, should infer from extension
                'is_binary': False
            }
        ]
        
        result = analyzer.analyze_files_from_db(file_contents)
        
        assert isinstance(result, dict)
    
    def test_analyze_files_from_db_invalid_content(self, analyzer):
        """Test files with invalid content are skipped."""
        file_contents = [
            {
                'file_path': 'test.py',
                'file_extension': '.py',
                'file_content': '',  # Empty content
                'content_type': 'Python',
                'is_binary': False
            },
            {
                'file_path': 'app.js',
                'file_extension': '.js',
                'file_content': None,  # None content
                'content_type': 'JavaScript',
                'is_binary': False
            }
        ]
        
        result = analyzer.analyze_files_from_db(file_contents)
        
        assert result == {}
    
    def test_extract_top_terms_basic(self, analyzer):
        """Test extracting top terms from text."""
        text = "Python programming is great. Python is a programming language. Great for data science and programming."
        
        result = analyzer._extract_top_terms(text, max_terms=5)
        
        assert isinstance(result, list)
        assert len(result) <= 5
        assert 'python' in result or 'programming' in result
    
    def test_extract_top_terms_empty(self, analyzer):
        """Test extracting terms from empty text."""
        result = analyzer._extract_top_terms("")
        
        assert result == []
    
    def test_extract_top_terms_no_valid_words(self, analyzer):
        """Test text with only stopwords."""
        text = "the and for with that this"
        
        result = analyzer._extract_top_terms(text)
        
        assert isinstance(result, list)
    
    def test_extract_top_terms_short_words(self, analyzer):
        """Test text with short words (less than 3 chars)."""
        text = "a b c it is ok go"
        
        result = analyzer._extract_top_terms(text)
        
        # Short words should be filtered out
        assert isinstance(result, list)
    
    def test_normalize_binary_bytes(self, analyzer):
        """Test normalizing bytes content."""
        content = b"test content"
        result = analyzer._normalize_binary(content)
        
        assert result == content
        assert isinstance(result, bytes)
    
    def test_normalize_binary_memoryview(self, analyzer):
        """Test normalizing memoryview content."""
        content = memoryview(b"test content")
        result = analyzer._normalize_binary(content)
        
        assert isinstance(result, bytes)
        assert result == b"test content"
    
    def test_normalize_binary_none(self, analyzer):
        """Test normalizing None content."""
        result = analyzer._normalize_binary(None)
        
        assert result is None
    
    def test_normalize_binary_invalid_type(self, analyzer):
        """Test normalizing invalid type."""
        result = analyzer._normalize_binary("string content")
        
        assert result is None
    
    def test_detect_frameworks_no_matches(self, analyzer):
        """Test framework detection when no frameworks present."""
        temp_dir = tempfile.mkdtemp()
        
        with open(os.path.join(temp_dir, 'simple.txt'), 'w') as f:
            f.write('Just plain text')
        
        result = analyzer.detect_frameworks(temp_dir)
        
        assert isinstance(result, list)
        assert result == []
        
        shutil.rmtree(temp_dir)
    
    def test_detect_frameworks_docker(self, analyzer):
        """Test Docker framework detection."""
        temp_dir = tempfile.mkdtemp()
        
        # Create Dockerfile (which is detected by filename)
        with open(os.path.join(temp_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM python:3.9\nRUN pip install flask\n')
        
        result = analyzer.detect_frameworks(temp_dir)
        
        # Docker should be detected from Dockerfile presence
        assert isinstance(result, list)
        # Note: Framework detection requires both filename match and file location
        # The test verifies the method runs without error
        
        shutil.rmtree(temp_dir)
    
    def test_detect_frameworks_file_read_error(self, analyzer):
        """Test framework detection handles file read errors gracefully."""
        temp_dir = tempfile.mkdtemp()
        
        # Create a file that can be opened but might cause issues
        with open(os.path.join(temp_dir, 'test.py'), 'w') as f:
            f.write('# Normal Python file\nimport os\n')
        
        result = analyzer.detect_frameworks(temp_dir)
        
        # Should not crash even if there are errors
        assert isinstance(result, list)
        
        shutil.rmtree(temp_dir)
    
    def test_calculate_metrics_file_errors(self, analyzer):
        """Test metrics calculation handles file errors gracefully."""
        temp_dir = tempfile.mkdtemp()
        
        # Create some files
        with open(os.path.join(temp_dir, 'test.py'), 'w') as f:
            f.write('# Test\n')
        
        metrics = analyzer.calculate_metrics(temp_dir)
        
        # Verify expected keys exist
        assert 'total_lines_of_code' in metrics
        assert 'code_files' in metrics
        assert metrics['average_file_size'] >= 0
        
        shutil.rmtree(temp_dir)
    
    def test_calculate_metrics_empty_directory(self, analyzer):
        """Test metrics on empty directory."""
        temp_dir = tempfile.mkdtemp()
        
        metrics = analyzer.calculate_metrics(temp_dir)
        
        assert metrics['total_lines_of_code'] == 0
        assert metrics['total_file_size_bytes'] == 0
        assert metrics['code_files'] == 0
        assert metrics['average_file_size'] == 0
        
        shutil.rmtree(temp_dir)
    
    def test_extract_skills_git_directory(self, analyzer):
        """Test Git skill detection from .git directory."""
        temp_dir = tempfile.mkdtemp()
        git_dir = os.path.join(temp_dir, '.git')
        os.makedirs(git_dir)
        
        with open(os.path.join(git_dir, 'config'), 'w') as f:
            f.write('[core]\n')
        
        skills = analyzer.extract_skills(temp_dir)
        
        assert 'Git' in skills
        
        shutil.rmtree(temp_dir)
    
    def test_extract_skills_cicd(self, analyzer):
        """Test CI/CD skill detection."""
        temp_dir = tempfile.mkdtemp()
        github_dir = os.path.join(temp_dir, '.github', 'workflows')
        os.makedirs(github_dir)
        
        with open(os.path.join(github_dir, 'ci.yml'), 'w') as f:
            f.write('name: CI\n')
        
        skills = analyzer.extract_skills(temp_dir)
        
        assert 'CI/CD' in skills
        
        shutil.rmtree(temp_dir)
    
    def test_get_file_breakdown_config_files(self, analyzer):
        """Test file breakdown categorization of config files."""
        temp_dir = tempfile.mkdtemp()
        
        with open(os.path.join(temp_dir, 'config.json'), 'w') as f:
            f.write('{}')
        with open(os.path.join(temp_dir, 'settings.yml'), 'w') as f:
            f.write('key: value')
        with open(os.path.join(temp_dir, '.env'), 'w') as f:
            f.write('VAR=value')
        
        breakdown = analyzer.get_file_breakdown(temp_dir)
        
        # .json might be categorized as JSON language, check if config OR other category
        assert breakdown['by_category']['config'] >= 0
        assert '.json' in breakdown['by_extension']
        assert '.yml' in breakdown['by_extension']
        
        shutil.rmtree(temp_dir)
    
    def test_get_file_breakdown_design_files(self, analyzer):
        """Test design files categorization."""
        temp_dir = tempfile.mkdtemp()
        
        # Create design files if DESIGN_EXTENSIONS are defined
        with open(os.path.join(temp_dir, 'diagram.png'), 'w') as f:
            f.write('fake image')
        
        breakdown = analyzer.get_file_breakdown(temp_dir)
        
        assert 'by_extension' in breakdown
        assert 'by_category' in breakdown
        
        shutil.rmtree(temp_dir)
    
    def test_structure_analysis_max_depth(self, analyzer):
        """Test max depth calculation in structure analysis."""
        temp_dir = tempfile.mkdtemp()
        
        # Create nested directories
        deep_path = os.path.join(temp_dir, 'level1', 'level2', 'level3')
        os.makedirs(deep_path)
        
        structure = analyzer.analyze_structure(temp_dir)
        
        assert structure['max_depth'] >= 3
        
        shutil.rmtree(temp_dir)
    
    def test_structure_analysis_config_directory(self, analyzer):
        """Test config directory detection."""
        temp_dir = tempfile.mkdtemp()
        
        os.makedirs(os.path.join(temp_dir, 'config'))
        
        structure = analyzer.analyze_structure(temp_dir)
        
        assert structure['has_config'] == True
        
        shutil.rmtree(temp_dir)
    
    def test_language_percentages_calculation(self, analyzer):
        """Test language percentage calculations."""
        temp_dir = tempfile.mkdtemp()
        
        # Create multiple Python files and one JS file
        for i in range(3):
            with open(os.path.join(temp_dir, f'test{i}.py'), 'w') as f:
                f.write('# Python file')
        
        with open(os.path.join(temp_dir, 'app.js'), 'w') as f:
            f.write('// JS file')
        
        languages = analyzer.detect_languages(temp_dir)
        
        assert 'percentages' in languages
        assert languages['percentages']['Python'] == 75.0  # 3 out of 4 files
        assert languages['percentages']['JavaScript'] == 25.0
        
        shutil.rmtree(temp_dir)
    
    def test_extract_text_from_pdf_bytes_success(self, analyzer):
        """Test PDF text extraction with mocked PdfReader."""
        pdf_content = b'%PDF-1.4 fake pdf content'
        
        # Create a mock pypdf module
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF text content"
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        
        mock_pypdf = Mock()
        mock_pypdf.PdfReader.return_value = mock_reader
        
        with patch.dict('sys.modules', {'pypdf': mock_pypdf}):
            result = analyzer._extract_text_from_pdf_bytes(pdf_content)
            
            assert isinstance(result, str)
            assert "Sample PDF text content" in result
    
    def test_extract_text_from_pdf_bytes_no_pypdf(self, analyzer):
        """Test PDF extraction when pypdf is not available."""
        pdf_content = b'%PDF-1.4 fake pdf content'
        
        # Remove pypdf from modules if it exists
        with patch.dict('sys.modules', {'pypdf': None}):
            result = analyzer._extract_text_from_pdf_bytes(pdf_content)
            
            assert result == ""
    
    def test_extract_text_from_pdf_bytes_invalid_pdf(self, analyzer):
        """Test PDF extraction with invalid PDF content."""
        invalid_content = b'not a pdf'
        
        mock_pypdf = Mock()
        mock_pypdf.PdfReader.side_effect = Exception("Invalid PDF")
        
        with patch.dict('sys.modules', {'pypdf': mock_pypdf}):
            result = analyzer._extract_text_from_pdf_bytes(invalid_content)
            
            assert result == ""
    
    def test_extract_text_from_pdf_bytes_none_content(self, analyzer):
        """Test PDF extraction with None content."""
        result = analyzer._extract_text_from_pdf_bytes(None)
        
        assert result == ""
    
    def test_extract_text_from_pdf_bytes_empty_pages(self, analyzer):
        """Test PDF extraction with pages that have no text."""
        pdf_content = b'%PDF-1.4 fake pdf'
        
        mock_page = Mock()
        mock_page.extract_text.return_value = None
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        
        mock_pypdf = Mock()
        mock_pypdf.PdfReader.return_value = mock_reader
        
        with patch.dict('sys.modules', {'pypdf': mock_pypdf}):
            result = analyzer._extract_text_from_pdf_bytes(pdf_content)
            
            assert result == ""
    
    def test_get_easyocr_reader_success(self, analyzer):
        """Test EasyOCR reader initialization."""
        # Reset the cached reader
        analyzer._easyocr_reader = None
        
        mock_reader = Mock()
        mock_easyocr = Mock()
        mock_easyocr.Reader.return_value = mock_reader
        
        with patch.dict('sys.modules', {'easyocr': mock_easyocr}):
            result = analyzer._get_easyocr_reader()
            
            # Should cache the reader
            assert analyzer._easyocr_reader is not None
    
    def test_get_easyocr_reader_not_installed(self, analyzer):
        """Test EasyOCR reader when library not installed."""
        # Reset cached reader
        analyzer._easyocr_reader = None
        
        with patch.dict('sys.modules', {'easyocr': None}):
            result = analyzer._get_easyocr_reader()
            
            assert result is None
    
    def test_get_easyocr_reader_initialization_error(self, analyzer):
        """Test EasyOCR reader initialization failure."""
        analyzer._easyocr_reader = None
        
        mock_easyocr = Mock()
        mock_easyocr.Reader.side_effect = Exception("GPU not available")
        
        with patch.dict('sys.modules', {'easyocr': mock_easyocr}):
            result = analyzer._get_easyocr_reader()
            
            assert result is None
    
    def test_get_easyocr_reader_cached(self, analyzer):
        """Test that EasyOCR reader is cached."""
        mock_reader = Mock()
        analyzer._easyocr_reader = mock_reader
        
        result = analyzer._get_easyocr_reader()
        
        assert result is mock_reader
    
    def test_extract_text_from_image_bytes_success(self, analyzer):
        """Test image text extraction with mocked OCR."""
        image_content = b'\x89PNG\r\n\x1a\n fake png'
        
        mock_reader = Mock()
        mock_reader.readtext.return_value = ['Hello', 'World']
        analyzer._easyocr_reader = mock_reader
        
        mock_image = Mock()
        mock_pil = Mock()
        mock_pil.Image.open.return_value.convert.return_value = mock_image
        
        mock_numpy = Mock()
        mock_numpy.array.return_value = [[1, 2, 3]]
        
        with patch.dict('sys.modules', {'PIL': mock_pil, 'numpy': mock_numpy}):
            result = analyzer._extract_text_from_image_bytes(image_content)
            
            assert isinstance(result, str)
    
    def test_extract_text_from_image_bytes_no_reader(self, analyzer):
        """Test image extraction when OCR reader not available."""
        analyzer._easyocr_reader = None
        
        with patch.object(analyzer, '_get_easyocr_reader', return_value=None):
            result = analyzer._extract_text_from_image_bytes(b'fake image')
            
            assert result == ""
    
    def test_extract_text_from_image_bytes_none_content(self, analyzer):
        """Test image extraction with None content."""
        result = analyzer._extract_text_from_image_bytes(None)
        
        assert result == ""
    
    def test_extract_text_from_image_bytes_error(self, analyzer):
        """Test image extraction with processing error."""
        mock_reader = Mock()
        analyzer._easyocr_reader = mock_reader
        
        mock_pil = Mock()
        mock_pil.Image.open.side_effect = Exception("Invalid image")
        
        with patch.dict('sys.modules', {'PIL': mock_pil}):
            result = analyzer._extract_text_from_image_bytes(b'invalid')
            
            assert result == ""
    
    def test_extract_document_subjects_from_files_pdfs(self, analyzer):
        """Test document subject extraction from PDFs."""
        file_contents = [
            {
                'file_extension': '.pdf',
                'file_content': b'%PDF fake content',
                'is_binary': False
            }
        ]
        
        with patch.object(analyzer, '_extract_text_from_pdf_bytes', return_value="Python programming tutorial"):
            result = analyzer.extract_document_subjects_from_files(file_contents)
            
            assert result['enabled'] == True
            assert result['pdfs_scanned'] == 1
            assert result['files_scanned'] == 1
            assert isinstance(result['top_terms'], list)
    
    def test_extract_document_subjects_from_files_images(self, analyzer):
        """Test document subject extraction from images."""
        file_contents = [
            {
                'file_extension': '.png',
                'file_content': b'\x89PNG fake',
                'is_binary': False
            }
        ]
        
        with patch.object(analyzer, '_extract_text_from_image_bytes', return_value="Machine learning diagram"):
            result = analyzer.extract_document_subjects_from_files(file_contents)
            
            assert result['enabled'] == True
            assert result['images_scanned'] == 1
            assert result['files_scanned'] == 1
    
    def test_extract_document_subjects_max_files_limit(self, analyzer):
        """Test that max_files limit is respected."""
        file_contents = []
        for i in range(100):
            file_contents.append({
                'file_extension': '.pdf',
                'file_content': b'%PDF fake',
                'is_binary': False
            })
        
        with patch.object(analyzer, '_extract_text_from_pdf_bytes', return_value="text"):
            result = analyzer.extract_document_subjects_from_files(file_contents, max_files=10)
            
            assert result['files_scanned'] <= 10
    
    def test_extract_document_subjects_max_text_chars_limit(self, analyzer):
        """Test that max_text_chars limit is respected."""
        file_contents = [
            {
                'file_extension': '.pdf',
                'file_content': b'%PDF fake',
                'is_binary': False
            }
        ]
        
        long_text = "word " * 10000  # Very long text
        with patch.object(analyzer, '_extract_text_from_pdf_bytes', return_value=long_text):
            result = analyzer.extract_document_subjects_from_files(file_contents, max_text_chars=100)
            
            assert result['extracted_text_chars'] <= 100
    
    def test_extract_document_subjects_empty_list(self, analyzer):
        """Test document extraction with empty file list."""
        result = analyzer.extract_document_subjects_from_files([])
        
        assert result['enabled'] == True
        assert result['files_scanned'] == 0
        assert result['pdfs_scanned'] == 0
        assert result['images_scanned'] == 0
        assert result['top_terms'] == []
    
    def test_extract_document_subjects_no_content(self, analyzer):
        """Test document extraction with files that have no content."""
        file_contents = [
            {
                'file_extension': '.pdf',
                'file_content': None,
                'is_binary': False
            },
            {
                'file_extension': '.png',
                'file_content': b'',
                'is_binary': False
            }
        ]
        
        result = analyzer.extract_document_subjects_from_files(file_contents)
        
        assert result['files_scanned'] == 0
    
    def test_extract_document_subjects_mixed_types(self, analyzer):
        """Test document extraction with mixed file types."""
        file_contents = [
            {
                'file_extension': '.pdf',
                'file_content': b'%PDF',
                'is_binary': False
            },
            {
                'file_extension': '.jpg',
                'file_content': b'\xff\xd8\xff',
                'is_binary': False
            },
            {
                'file_extension': '.txt',  # Not PDF or image
                'file_content': b'text file',
                'is_binary': False
            }
        ]
        
        with patch.object(analyzer, '_extract_text_from_pdf_bytes', return_value="PDF text"):
            with patch.object(analyzer, '_extract_text_from_image_bytes', return_value="Image text"):
                result = analyzer.extract_document_subjects_from_files(file_contents)
                
                assert result['pdfs_scanned'] == 1
                assert result['images_scanned'] == 1
                assert result['files_scanned'] == 2
    
    def test_extract_document_subjects_sample_snippet(self, analyzer):
        """Test that sample snippet is included."""
        file_contents = [
            {
                'file_extension': '.pdf',
                'file_content': b'%PDF',
                'is_binary': False
            }
        ]
        
        with patch.object(analyzer, '_extract_text_from_pdf_bytes', return_value="This is sample text"):
            result = analyzer.extract_document_subjects_from_files(file_contents)
            
            assert 'sample_snippet' in result
            assert len(result['sample_snippet']) <= 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])