import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from resume.resume_manager import ResumeManager


class TestCustomResumeWordingUnit:

    @patch('resume.resume_manager.ResumeManager.store_user_resume')
    @patch('resume.resume_manager.ResumeManager.get_user_resume')
    def test_save_custom_wording_writes_map(self, mock_get, mock_store):
        mock_get.return_value = {"resume_data": {"custom_project_wording": {}}}
        mock_store.return_value = True

        ok = ResumeManager.save_custom_project_wording("u", 12, "Hello")
        assert ok is True

        args, _ = mock_store.call_args
        assert args[0] == "u"
        saved_resume_data = args[1]
        assert saved_resume_data["custom_project_wording"]["12"] == "Hello"

    @patch('resume.resume_manager.ResumeManager.store_user_resume')
    @patch('resume.resume_manager.ResumeManager.get_user_resume')
    def test_save_empty_clears(self, mock_get, mock_store):
        mock_get.return_value = {"resume_data": {"custom_project_wording": {"12": "Old"}}}
        mock_store.return_value = True

        ok = ResumeManager.save_custom_project_wording("u", 12, "   ")
        assert ok is True

        args, _ = mock_store.call_args
        saved_resume_data = args[1]
        assert "12" not in saved_resume_data["custom_project_wording"]

    @patch('resume.resume_manager.ResumeManager.store_user_resume')
    @patch('resume.resume_manager.ResumeManager.get_user_resume')
    def test_clear_calls_save_empty(self, mock_get, mock_store):
        mock_get.return_value = {"resume_data": {"custom_project_wording": {"12": "Old"}}}
        mock_store.return_value = True

        ok = ResumeManager.clear_custom_project_wording("u", 12)
        assert ok is True
