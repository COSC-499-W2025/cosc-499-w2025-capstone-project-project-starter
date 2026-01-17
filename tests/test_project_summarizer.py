# tests/test_project_summarizer.py
import sys
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from src.project_summarizer import ProjectSummarizer, summarize_project, get_available_projects


class TestProjectSummarizer:
    """Test suite for ProjectSummarizer functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.summarizer = ProjectSummarizer()
        
        # Sample project info
        self.sample_project_info = {
            'id': 1,
            'filename': 'test_project.zip',
            'created_at': datetime(2024, 1, 1, 10, 0, 0)
        }
        
        # Sample file contents
        self.sample_file_contents = [
            {
                'id': 1,
                'file_path': 'test_project/main.py',
                'file_name': 'main.py',
                'file_extension': '.py',
                'file_size': 1024,
                'file_content': '50',
                'content_type': 'text/x-python',
                'is_binary': False,
                'created_at': datetime(2024, 1, 1, 10, 0, 0)
            },
            {
                'id': 2,
                'file_path': 'test_project/README.md',
                'file_name': 'README.md',
                'file_extension': '.md',
                'file_size': 512,
                'file_content': '25',
                'content_type': 'text/markdown',
                'is_binary': False,
                'created_at': datetime(2024, 1, 1, 10, 5, 0)
            },
            {
                'id': 3,
                'file_path': 'test_project/src/utils.py',
                'file_name': 'utils.py',
                'file_extension': '.py',
                'file_size': 256,
                'file_content': '30',
                'content_type': 'text/x-python',
                'is_binary': False,
                'created_at': datetime(2024, 1, 1, 10, 10, 0)
            }
        ]
        
        # Sample file statistics
        self.sample_file_stats = {
            'total_files': 3,
            'total_size_bytes': 1792,
            'text_files': 3,
            'binary_files': 0,
            'file_extensions': [
                {'extension': '.py', 'count': 2},
                {'extension': '.md', 'count': 1}
            ],
            'folders': [
                {'folder': 'test_project', 'file_count': 3}
            ]
        }
    
    def test_language_detection_basic(self):
        """Test basic language detection functionality"""
        languages = self.summarizer._detect_languages(self.sample_file_contents)
        
        assert languages['primary_language'] == 'Python'
        assert languages['total_programming_files'] >= 2
        assert 'languages' in languages
        assert 'Python' in languages['languages']
        assert len(languages['languages']) >= 1
    
    def test_language_detection_no_files(self):
        """Test language detection with no files"""
        languages = self.summarizer._detect_languages([])
        
        assert languages['primary_language'] == 'Unknown'
        assert languages['total_programming_files'] == 0
        assert len(languages.get('languages', [])) == 0
    
    def test_language_detection_multiple_languages(self):
        """Test language detection with multiple programming languages"""
        multi_lang_files = [
            {'file_extension': '.py', 'file_name': 'main.py'},
            {'file_extension': '.js', 'file_name': 'app.js'},
            {'file_extension': '.java', 'file_name': 'Main.java'},
            {'file_extension': '.cpp', 'file_name': 'main.cpp'},
            {'file_extension': '.py', 'file_name': 'utils.py'}
        ]
        
        languages = self.summarizer._detect_languages(multi_lang_files)
        
        assert languages['primary_language'] == 'Python'
        assert languages['total_programming_files'] == 5
        assert 'Python' in languages['languages']
        assert len(languages['languages']) <= 5
    
    
    def test_collaboration_analysis_individual(self):
        """Test collaboration analysis for individual projects"""
        collaboration = self.summarizer._analyze_collaboration( 0)
        
        assert 'collaboration_level' in collaboration
        assert 'indicators' in collaboration
        assert 'analysis' in collaboration
        assert collaboration['indicators']['collaboration_score'] >= 0
        assert collaboration['indicators']['collaboration_score'] <= 100
    
    @patch('src.project_summarizer.get_file_contents_by_upload_id')
    @patch('collaborative.identify_projects.identify_contributors')
    @patch('collaborative.identify_projects.get_zip_file')
    def test_collaboration_analysis_team_project(self, mock_get_zip, mock_identify_contributors, mock_get_files):
        """Test collaboration analysis when project data shows a team project"""
        # 1 Mock what would come from the database via get_file_contents_by_upload_id()
        mock_get_files.return_value = [
            {'file_name': '.gitignore', 'file_path': '.gitignore'},
            {'file_name': 'team_utils.py', 'file_path': 'src/team_utils.py'},
            {'file_name': 'shared_config.py', 'file_path': 'src/shared_config.py'},
            {'file_name': 'common_helpers.py', 'file_path': 'src/common_helpers.py'},
        ]

        # 2 Pretend a ZIP file exists in storage
        mock_get_zip.return_value = b'fake-zip-bytes'

        # 3 Fake identify_contributors() object with multiple commit authors
        fake_ic = Mock()
        fake_ic.extract_repo.return_value = '/tmp/fake_repo'
        fake_ic.get_commit_counts.return_value = {
            'Alice <alice@example.com>': 5,
            'Bob <bob@example.com>': 3,
        }
        fake_ic.cleanup.return_value = None
        mock_identify_contributors.return_value = fake_ic

        # 4 Call the method using a dummy project_id that triggers the mocks
        project_id = 99
        collaboration = self.summarizer._analyze_collaboration(project_id)

        # 5 Assertions – high collaboration score and multiple indicators
        assert collaboration['indicators']['git_files'] > 0
        assert collaboration['indicators']['team_structure']
        assert collaboration['indicators']['collaboration_score'] >= 70
        assert collaboration['collaboration_level'] in {
            'Likely team project', 'Definitely collaborative'
        }

        # 6 Optional: verify analysis mentions both contributors
        analysis_text = collaboration['analysis']
        assert 'Alice' in analysis_text
        assert 'Bob' in analysis_text
        
    def test_time_analysis_basic(self):
        """Test basic time analysis functionality"""
        time_analysis = self.summarizer._analyze_time_patterns(self.sample_file_contents)
        
        assert 'duration_days' in time_analysis
        assert 'intensity' in time_analysis
        assert 'first_file' in time_analysis
        assert 'last_file' in time_analysis
        
        assert time_analysis['intensity'] == 'Single day'
        assert time_analysis['duration_days'] == 0
    
    def test_time_analysis_long_term_project(self):
        """Test time analysis for long-term projects"""
        long_term_files = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(10):
            file_date = base_date + timedelta(days=i*6)
            long_term_files.append({
                'created_at': file_date
            })
        
        time_analysis = self.summarizer._analyze_time_patterns(long_term_files)
        
        assert time_analysis['intensity'] == 'Long-term (>1 month)'
        assert time_analysis['duration_days'] > 30
    
    def test_time_analysis_no_timestamps(self):
        """Test time analysis with no timestamp data"""
        files_no_time = [
            {'file_name': 'test.py'},
            {'file_name': 'test2.py'}
        ]
        
        time_analysis = self.summarizer._analyze_time_patterns(files_no_time)
        
        assert time_analysis == {}
    
    @patch('src.project_summarizer.AuthManager')
    @patch('src.project_summarizer.get_project_by_id')
    def test_generate_project_summary_project_not_found(self, mock_project, mock_auth):
        """Test project summary generation when project is not found"""
        # Mock AuthManager to return a valid username
        mock_auth.get_current_username.return_value = 'test_user'
        mock_project.return_value = None
        
        summary = self.summarizer.generate_project_summary(999)
        
        assert 'error' in summary
        assert summary['error'] == 'Project not found or access denied'
    
    @patch('src.project_summarizer.AuthManager')
    @patch('src.project_summarizer.get_project_by_id')
    @patch('src.project_summarizer.get_file_contents_by_upload_id')
    def test_generate_project_summary_no_file_contents(self, mock_contents, mock_project, mock_auth):
        """Test project summary generation when no file contents are found"""
        # Mock AuthManager to return a valid username
        mock_auth.get_current_username.return_value = 'test_user'
        mock_project.return_value = self.sample_project_info
        mock_contents.return_value = []
        
        summary = self.summarizer.generate_project_summary(1)
        
        assert 'error' in summary
        assert summary['error'] == 'No file contents found for this project'
    
    def test_format_summary_for_display(self):
        """Test summary formatting for display"""
        sample_summary = {
            'project_info': {
                'id': 1,
                'filename': 'test_project.zip',
                'created_at': '2024-01-01 10:00:00'
            },
            'languages': {
                'primary_language': 'Python',
                'languages': ['Python', 'Markdown'],
                'total_programming_files': 2
            },
            'collaboration_analysis': {
                'collaboration_level': 'Possibly collaborative',
                'indicators': {'collaboration_score': 40},
                'analysis': 'Based on file structure and Git presence.'
            },
            'time_analysis': {
                'duration_days': 0,
                'intensity': 'Single day',
                'first_file': '2024-01-01',
                'last_file': '2024-01-01'
            },
            'file_statistics': {
                'total_files': 3,
                'text_files': 3,
                'binary_files': 0,
                'total_size_bytes': 1792
            },
            'code_analysis': {
                'oop_principles_summary': {
                    'abstraction': {'count': 0, 'examples': []},
                    'encapsulation': {'count': 1, 'examples': []}
                },
                'code_quality_summary': {
                    'average_quality_score': 45.0,
                    'strengths': ['Uses abstraction']
                }
            }
        }
        
        formatted = self.summarizer.format_summary_for_display(sample_summary)
        
        assert 'PROJECT SUMMARY: test_project.zip' in formatted
        assert 'Overview:' in formatted
        assert 'Primary Language: Python' in formatted
        assert 'CODE ANALYSIS & TECHNICAL INSIGHTS' in formatted
        assert 'Object-Oriented Programming Principles:' in formatted
    
    def test_format_summary_for_display_error(self):
        """Test summary formatting when there's an error"""
        error_summary = {'error': 'Test error message'}
        
        formatted = self.summarizer.format_summary_for_display(error_summary)
        
        assert 'Error: Test error message' in formatted


class TestSummarizeProjectFunction:
    """Test suite for the convenience summarize_project function"""
    
    @patch('src.project_summarizer.AuthManager')
    @patch('src.project_summarizer.ProjectSummarizer')
    def test_summarize_project_success(self, mock_summarizer_class, mock_auth):
        """Test the summarize_project convenience function"""
        # Mock AuthManager to return a valid username
        mock_auth.get_current_username.return_value = 'test_user'
        
        # Mock the summarizer instance
        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        
        # Mock the summary generation and formatting
        mock_summary = {'test': 'summary'}
        mock_formatted = 'Formatted summary output'
        mock_summarizer.generate_project_summary.return_value = mock_summary
        mock_summarizer.format_summary_for_display.return_value = mock_formatted
        
        result = summarize_project(1)
        
        # Verify the function calls
        mock_summarizer_class.assert_called_once()
        # Verify generate_project_summary called with user_name parameter
        mock_summarizer.generate_project_summary.assert_called_once_with(1, user_name='test_user')
        mock_summarizer.format_summary_for_display.assert_called_once_with(mock_summary)
        
        assert result == mock_formatted


class TestGetAvailableProjects:
    """Test suite for the get_available_projects function"""
    
    @patch('src.project_summarizer.AuthManager')
    @patch('src.project_summarizer.with_db_cursor')
    def test_get_available_projects_success(self, mock_with_db_cursor, mock_auth):
        """Test successful retrieval of available projects"""
        # Mock AuthManager to return a valid username
        mock_auth.get_current_username.return_value = 'test_user'
        
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database results
        mock_projects = [
            (1, 'project1.zip', datetime(2024, 1, 1, 10, 0, 0)),
            (2, 'project2.zip', datetime(2024, 1, 2, 11, 0, 0))
        ]
        mock_cursor.fetchall.return_value = mock_projects
        
        projects = get_available_projects()
        
        # Verify the function calls
        mock_with_db_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
        
        # Check results
        assert len(projects) == 2
        assert projects[0]['id'] == 1
        assert projects[0]['filename'] == 'project1.zip'
        assert projects[1]['id'] == 2
        assert projects[1]['filename'] == 'project2.zip'
    
    @patch('src.project_summarizer.with_db_cursor')
    def test_get_available_projects_no_connection(self, mock_with_db_cursor):
        """Test get_available_projects when database connection fails"""
        mock_with_db_cursor.side_effect = ConnectionError("Could not connect to database")
        
        projects = get_available_projects()
        
        assert projects == []
    
    @patch('src.project_summarizer.with_db_cursor')
    def test_get_available_projects_database_error(self, mock_with_db_cursor):
        """Test get_available_projects when database query fails"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database error
        mock_cursor.execute.side_effect = Exception("Database error")
        
        projects = get_available_projects()
        
        assert projects == []

if __name__ == '__main__':
    pytest.main([__file__])
