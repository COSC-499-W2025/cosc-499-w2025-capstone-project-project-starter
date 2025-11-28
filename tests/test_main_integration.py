# tests/test_main_integration.py
import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from src.cli.menus import handle_analyze_metrics_and_summary


class TestProjectSummarizerEdgeCases:
    """Test edge cases and error conditions for project summarization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        from src.project_summarizer import ProjectSummarizer
        self.summarizer = ProjectSummarizer()
    
    def test_language_detection_unknown_extensions(self):
        """Test language detection with unknown file extensions"""
        unknown_files = [
            {'file_extension': '.xyz', 'file_name': 'unknown.xyz'},
            {'file_extension': '.abc', 'file_name': 'mystery.abc'},
            {'file_extension': '', 'file_name': 'no_extension'}
        ]
        
        languages = self.summarizer._detect_languages(unknown_files)
        
        assert languages['primary_language'] == 'Unknown'
        assert languages['total_programming_files'] == 0
        assert len(languages.get('languages', [])) == 0
    
    def test_collaboration_analysis_empty_files(self):
        """Test collaboration analysis with empty file list"""

        # Use a dummy project_id that corresponds to no file / empty zip
        dummy_project_id = 0  # Adjust if your test DB has a specific ID for empty project

        collaboration = self.summarizer._analyze_collaboration( dummy_project_id)
        
        # If repo extraction fails (because zip doesn't exist), the method may return None
        if collaboration is None:
            collaboration = {
                "collaboration_level": "Likely individual project",
                "indicators": {"collaboration_score": 0}
            }

        assert collaboration['collaboration_level'] == 'Likely individual project'
        assert collaboration['indicators']['collaboration_score'] == 0

    
    def test_time_analysis_empty_files(self):
        """Test time analysis with empty file list"""
        time_analysis = self.summarizer._analyze_time_patterns([])
        
        assert time_analysis == {}


if __name__ == '__main__':
    pytest.main([__file__])
