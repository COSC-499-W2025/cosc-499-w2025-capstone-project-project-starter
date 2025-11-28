# tests/test_portfolio_manager.py
import sys
import os
import pytest
from unittest.mock import Mock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_manager import PortfolioManager


class TestPortfolioManager:
    """Test suite for PortfolioManager functionality"""
    
    def setup_method(self):
        self.user_id = 'test_user'
        self.manager = PortfolioManager(self.user_id)
    
    @patch('portfolio.portfolio_manager.rank_all_projects')
    def test_generate_portfolio_report_no_projects(self, mock_rank_all):
        """Test portfolio generation when no projects exist"""
        mock_rank_all.return_value = []
        result = self.manager.generate_portfolio_report()
        assert 'error' in result
        assert result['error'] == 'No projects found'
        assert 'timestamp' in result
    
    @patch('portfolio.portfolio_manager.rank_all_projects')
    def test_generate_portfolio_report_exception_handling(self, mock_rank_all):
        """Test exception handling in portfolio generation"""
        mock_rank_all.side_effect = Exception("Database error")
        result = self.manager.generate_portfolio_report()
        assert 'error' in result
        assert 'timestamp' in result
    
    def test_generate_project_summary_text_basic(self):
        """Test project summary text generation"""
        summary = {
            'project_info': {'filename': 'test.zip'},
            'languages': {'primary_language': 'Python', 'languages': ['Python']}
        }
        result = self.manager._generate_project_summary_text(
            summary, {}, {'totals': {'files': 10, 'lines': 1000}}, []
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert 'Python' in result
    
    @patch('portfolio.portfolio_manager.get_file_contents_by_upload_id')
    @patch('portfolio.portfolio_manager.list_projects_chronologically')
    def test_get_chronological_skills(self, mock_list_projects, mock_get_files):
        """Test chronological skills listing"""
        from datetime import datetime
        
        mock_list_projects.return_value = [
            {
                'id': 1,
                'filename': 'project1.zip',
                'created_at': datetime(2024, 1, 1),
                'file_count': 5
            },
            {
                'id': 2,
                'filename': 'project2.zip',
                'created_at': datetime(2024, 1, 15),
                'file_count': 3
            }
        ]
        
        mock_get_files.side_effect = [
            [{'file_name': 'main.py', 'file_path': 'src/main.py'}],
            [{'file_name': 'test.py', 'file_path': 'tests/test.py'}]
        ]
        
        with patch.object(self.manager.project_analyzer, '_extract_skills_from_files') as mock_extract:
            mock_extract.side_effect = [
                ['Python', 'Flask'],
                ['Python', 'pytest']
            ]
            
            result = self.manager.get_chronological_skills()
            
            assert len(result) == 3  # Python appears twice but tracked once
            assert result[0]['skill'] == 'Python'
            assert result[0]['first_used_date'] == datetime(2024, 1, 1)
            assert 'Flask' in [s['skill'] for s in result]
            assert 'pytest' in [s['skill'] for s in result]
    
    @patch('portfolio.portfolio_manager.list_projects_chronologically')
    def test_get_chronological_skills_no_projects(self, mock_list_projects):
        """Test chronological skills when no projects exist"""
        mock_list_projects.return_value = []
        result = self.manager.get_chronological_skills()
        assert result == []
    
    @patch('portfolio.portfolio_manager.list_projects_chronologically')
    def test_get_chronological_skills_exception(self, mock_list_projects):
        """Test chronological skills with exception handling"""
        mock_list_projects.side_effect = Exception("Database error")
        result = self.manager.get_chronological_skills()
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

