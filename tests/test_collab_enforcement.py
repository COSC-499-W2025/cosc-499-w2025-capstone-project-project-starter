import datetime
import pytest
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Adjust this import to your actual module path
from project_summarizer import ProjectSummarizer


def test_analyze_collaboration_when_user_collab_denied(monkeypatch):
    """
    If get_user_collaboration() returns a truthy tuple whose first element is False,
    _analyze_collaboration should return the 'collaboration not granted' result and
    NOT attempt further collaboration analysis.
    """

    # 1) Fake file contents (doesn't really matter for this branch)
    monkeypatch.setattr(
        "project_summarizer.get_file_contents_by_upload_id",
        lambda project_id: [],
    )

    # 2) Simplify these indicator helpers so they don't touch DB / other logic
    monkeypatch.setattr(
        "project_summarizer._count_git_files",
        lambda file_contents: 0,
    )
    monkeypatch.setattr(
        "project_summarizer._detect_team_structure",
        lambda file_contents: {},
    )

    # 3) Key patch: user collaboration returns a tuple with first element False
    monkeypatch.setattr(
        "project_summarizer.get_user_collaboration",
        lambda user_name: (False, datetime.datetime(2025, 1, 1, 0, 0, 0)),
    )
    
    # 4) Mock AuthManager to return a username
    monkeypatch.setattr(
        "project_summarizer.AuthManager.get_current_username",
        lambda: "test_user",
    )

    summarizer = ProjectSummarizer()
    result = summarizer._analyze_collaboration(project_id=1)

    # --- Assertions ---
    assert result["collaboration_level"] == "collaboration not granted"
    assert result["analysis"] == "collaboration not granted"

    indicators = result["indicators"]
    # indicators come from the early setup
    assert indicators["git_files"] == 0
    assert indicators["team_structure"] == {}
    assert indicators["has_common_names"] is False
    assert indicators["collaboration_score"] == 0
