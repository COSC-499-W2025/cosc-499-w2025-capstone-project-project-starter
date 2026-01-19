import builtins
import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.resume_manager import ResumeManager


def test_save_custom_project_wording_updates_resume_data(monkeypatch):
    user_id = "u1"
    project_id = 15
    wording = "My custom wording"

    # Mock existing resume
    monkeypatch.setattr(
        ResumeManager,
        "get_user_resume",
        lambda uid: {"resume_data": {"user_id": uid, "top_projects": []}, "created_at": None, "updated_at": None}
    )

    captured = {}

    def fake_store(uid, resume_data):
        captured["uid"] = uid
        captured["resume_data"] = resume_data
        return True

    monkeypatch.setattr(ResumeManager, "store_user_resume", fake_store)

    ok = ResumeManager.save_custom_project_wording(user_id, project_id, wording)
    assert ok is True
    assert captured["uid"] == user_id
    assert captured["resume_data"]["custom_project_wording"][str(project_id)] == wording


def test_clear_custom_project_wording_removes_entry(monkeypatch):
    user_id = "u1"
    project_id = 15

    # Start with wording already present
    monkeypatch.setattr(
        ResumeManager,
        "get_user_resume",
        lambda uid: {
            "resume_data": {"custom_project_wording": {str(project_id): "hello"}},
            "created_at": None,
            "updated_at": None,
        }
    )

    captured = {}

    def fake_store(uid, resume_data):
        captured["resume_data"] = resume_data
        return True

    monkeypatch.setattr(ResumeManager, "store_user_resume", fake_store)

    ok = ResumeManager.clear_custom_project_wording(user_id, project_id)
    assert ok is True
    assert "custom_project_wording" in captured["resume_data"]
    assert str(project_id) not in captured["resume_data"]["custom_project_wording"]


def test_list_custom_worded_projects_returns_ids(monkeypatch):
    user_id = "u1"

    monkeypatch.setattr(
        ResumeManager,
        "get_user_resume",
        lambda uid: {
            "resume_data": {
                "custom_project_wording": {
                    "15": "A",
                    "23": "B",
                    "999": "   ",   # blank should be ignored
                    "abc": "X",     # non-int key ignored
                }
            },
            "created_at": None,
            "updated_at": None,
        }
    )

    ids = ResumeManager.list_custom_worded_projects(user_id)
    assert ids == [15, 23]


def test_generate_user_resume_uses_custom_wording(monkeypatch):
    user_id = "u1"
    project_id = 15
    custom_text = "Built a scalable resume system with user-controlled content."

    # 1) Mock ranking output
    monkeypatch.setattr(
        "resume.resume_manager.rank_all_projects",
        lambda user_name=None: [{"project_id": project_id, "filename": "many_files.zip", "score": 99.0}]
    )

    # 2) Avoid author detection / prompts
    monkeypatch.setattr("resume.resume_manager.get_file_contents_by_upload_id", lambda pid: [])
    monkeypatch.setattr("resume.resume_manager._identify_authors_from_zip", lambda pid: set())
    monkeypatch.setattr("resume.resume_manager._extract_common_names_from_filenames", lambda fc: set())
    monkeypatch.setattr("resume.resume_manager.get_user_git_username", lambda: None)

    # If any input() happens, return empty to proceed
    monkeypatch.setattr(builtins, "input", lambda *args, **kwargs: "")

    # 3) Mock stored resume containing custom wording map
    monkeypatch.setattr(
        ResumeManager,
        "get_user_resume",
        lambda uid: {
            "resume_data": {"custom_project_wording": {str(project_id): custom_text}},
            "created_at": None,
            "updated_at": None,
        }
    )

    # 4) These fallbacks should NOT win over custom wording, but keep them safe
    monkeypatch.setattr("resume.resume_manager.get_stored_ranking_by_project_id", lambda pid: {"summary": "DB summary"})
    monkeypatch.setattr("resume.resume_manager.summarize_project", lambda pid, user_name=None: "LLM summary")

    # 5) Minimal summarizer output so resume generation continues
    class DummySummarizer:
        def generate_project_summary(self, pid, user_name=None):
            return {
                "languages": {"languages": ["Python"], "primary_language": "Python"},
                "time_analysis": {"duration_days": 1, "intensity": "Short", "first_file": "", "last_file": ""},
                "collaboration_analysis": {"collaboration_level": "Unknown"},
                "code_analysis": {},
                "project_info": {},
            }

    monkeypatch.setattr("resume.resume_manager.ProjectSummarizer", lambda: DummySummarizer())

    # 6) Minimal SkillMapper
    class DummySkillMapper:
        def extract_skills_from_deep_analysis(self, code_analysis):
            return []
        def categorize_skills(self, skills):
            return {}

    monkeypatch.setattr("resume.resume_manager.SkillMapper", lambda: DummySkillMapper())

    data = ResumeManager.generate_user_resume(user_id, top_projects_count=1)
    assert data is not None
    assert data["top_projects"][0]["project_id"] == project_id
    assert data["top_projects"][0]["summary"] == custom_text
