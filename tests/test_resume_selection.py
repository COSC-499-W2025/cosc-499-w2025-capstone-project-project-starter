import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.resume_manager import ResumeManager


class TestResumeSelection:
    """
    Tests for resume content selection:
    - include_skills flag
    - skills_mode ("categorized" vs "all")
    """

    @patch('resume.resume_manager.get_stored_ranking_by_project_id')
    @patch('resume.resume_manager.get_user_git_username')
    @patch('resume.resume_manager.get_file_contents_by_upload_id')
    @patch('resume.resume_manager.SkillMapper')
    @patch('resume.resume_manager.ProjectSummarizer')
    @patch('resume.resume_manager.get_stored_rankings')
    @patch('resume.resume_manager.rank_all_projects')
    def test_generate_user_resume_include_skills_false(
        self,
        mock_rank,
        mock_get_stored_rankings,
        mock_summarizer_class,
        mock_skill_mapper_class,
        mock_get_files,
        mock_git_username,
        mock_stored_ranking
    ):
        mock_git_username.return_value = None

        # Return empty stored rankings so fallback to rank_all_projects
        mock_get_stored_rankings.return_value = []

        # --- ranking/project mocks ---
        mock_rank.return_value = [
            {'project_id': 1, 'filename': 'project1.zip', 'score': 100},
        ]

        # --- summary stored ---
        mock_stored_ranking.return_value = {'summary': 'Stored summary'}

        # --- summarizer mock ---
        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer.generate_project_summary.return_value = {
            'languages': {
                'primary_language': 'Python',
                'languages': ['Python']
            },
            'time_analysis': {
                'duration_days': 10,
                'intensity': 'High',
                'first_file': '2024-01-01',
                'last_file': '2024-01-10'
            },
            'collaboration_analysis': {
                'collaboration_level': 'Team'
            },
            'code_analysis': {
                'code_quality_summary': {'average_quality_score': 80.0}
            },
            'project_info': {
                'filename': 'project1.zip',
                'created_at': '2024-01-01'
            }
        }

        # --- skills mapper mock ---
        mock_skill_mapper = Mock()
        mock_skill_mapper_class.return_value = mock_skill_mapper
        mock_skill_mapper.extract_skills_from_deep_analysis.return_value = ['OOP']
        mock_skill_mapper.categorize_skills.return_value = {'Concepts': ['OOP']}

        # --- file contents/frameworks ---
        mock_get_files.return_value = [
            {'file_name': 'package.json'},
            {'file_name': 'App.jsx'},
        ]

        selection = {
            "include_skills": False,        # <-- main point
            "skills_mode": "categorized"
        }

        result = ResumeManager.generate_user_resume("test_user", top_projects_count=1, selection=selection)

        assert result is not None
        assert result["user_name"] == "test_user"

        # Skills should be empty but keys must still exist
        assert result["all_skills"] == []
        assert result["categorized_skills"] == {}

        # Per-project skills should also be empty list
        assert len(result["top_projects"]) == 1
        assert result["top_projects"][0]["skills"] == []

    @patch('resume.resume_manager.get_stored_ranking_by_project_id')
    @patch('resume.resume_manager.get_user_git_username')
    @patch('resume.resume_manager.get_file_contents_by_upload_id')
    @patch('resume.resume_manager.SkillMapper')
    @patch('resume.resume_manager.ProjectSummarizer')
    @patch('resume.resume_manager.get_stored_rankings')
    @patch('resume.resume_manager.rank_all_projects')
    def test_generate_user_resume_skills_mode_all(
        self,
        mock_rank,
        mock_get_stored_rankings,
        mock_summarizer_class,
        mock_skill_mapper_class,
        mock_get_files,
        mock_git_username,
        mock_stored_ranking
    ):
        mock_git_username.return_value = None

        # Return empty stored rankings so fallback to rank_all_projects
        mock_get_stored_rankings.return_value = []

        mock_rank.return_value = [
            {'project_id': 1, 'filename': 'project1.zip', 'score': 100},
        ]

        mock_stored_ranking.return_value = {'summary': 'Stored summary'}

        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer.generate_project_summary.return_value = {
            'languages': {
                'primary_language': 'Python',
                'languages': ['Python']
            },
            'time_analysis': {
                'duration_days': 10,
                'intensity': 'High',
                'first_file': '2024-01-01',
                'last_file': '2024-01-10'
            },
            'collaboration_analysis': {
                'collaboration_level': 'Team'
            },
            'code_analysis': {
                'code_quality_summary': {'average_quality_score': 80.0}
            },
            'project_info': {
                'filename': 'project1.zip',
                'created_at': '2024-01-01'
            }
        }

        mock_skill_mapper = Mock()
        mock_skill_mapper_class.return_value = mock_skill_mapper
        mock_skill_mapper.extract_skills_from_deep_analysis.return_value = ['OOP']
        mock_skill_mapper.categorize_skills.return_value = {'Concepts': ['OOP']}  # should NOT be used when skills_mode="all"

        mock_get_files.return_value = [
            {'file_name': 'package.json'},
            {'file_name': 'App.jsx'},
        ]

        selection = {
            "include_skills": True,
            "skills_mode": "all"            # <-- main point
        }

        result = ResumeManager.generate_user_resume("test_user", top_projects_count=1, selection=selection)

        assert result is not None

        # all_skills should have content (languages/frameworks/deep skills)
        assert isinstance(result["all_skills"], list)
        assert len(result["all_skills"]) > 0

        # skills_mode="all" => categorized_skills should be empty
        assert result["categorized_skills"] == {}
