"""
Tests for individual contributor Git analytics.
Creates a temporary Git repository and validates per-author metrics.
"""
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import pytest


@pytest.fixture
def multi_author_repo():
    """
    Create a temporary Git repo with two authors:
    - Author A: 6 commits
    - Author B: 4 commits
    Total: 10 commits across multiple files and weeks.
    """
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        
        # Base date for commits
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        commits_data = [
            # Author A commits (6 total)
            ("author_a@example.com", "Author A", "feat: initial implementation", base_date, "module1.py"),
            ("author_a@example.com", "Author A", "fix: resolve startup bug", base_date + timedelta(days=1), "module1.py"),
            ("author_a@example.com", "Author A", "feat: add user authentication", base_date + timedelta(days=3), "auth.py"),
            ("author_a@example.com", "Author A", "test: add auth tests", base_date + timedelta(days=8), "test_auth.py"),
            ("author_a@example.com", "Author A", "refactor: clean up module1", base_date + timedelta(days=10), "module1.py"),
            ("author_a@example.com", "Author A", "docs: update README", base_date + timedelta(days=12), "README.md"),
            
            # Author B commits (4 total)
            ("author_b@example.com", "Author B", "feat: add dashboard", base_date + timedelta(days=2), "dashboard.py"),
            ("author_b@example.com", "Author B", "fix: fix dashboard layout", base_date + timedelta(days=4), "dashboard.py"),
            ("author_b@example.com", "Author B", "add new widget", base_date + timedelta(days=9), "widget.py"),
            ("author_b@example.com", "Author B", "test: add widget tests", base_date + timedelta(days=11), "test_widget.py"),
        ]
        
        for email, name, message, commit_date, filename in commits_data:
            # Set git author for this commit
            subprocess.run(
                ["git", "config", "user.name", name],
                cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", email],
                cwd=repo_path, check=True, capture_output=True
            )
            
            # Create/modify file with varying content to generate insertions
            file_path = repo_path / filename
            with open(file_path, "a") as f:
                f.write(f"# Content added at {commit_date}\n")
                f.write(f"# {message}\n")
                f.write(f"def function_{len(message)}():\n")
                f.write(f"    pass\n\n")
            
            # Stage and commit with specific date
            subprocess.run(["git", "add", filename], cwd=repo_path, check=True, capture_output=True)
            
            date_str = commit_date.strftime("%Y-%m-%d %H:%M:%S")
            env = os.environ.copy()
            env["GIT_AUTHOR_DATE"] = date_str
            env["GIT_COMMITTER_DATE"] = date_str
            
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path, check=True, capture_output=True, env=env
            )
        
        yield repo_path
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_summarize_author_contrib_basic_stats(multi_author_repo):
    """Test basic author contribution statistics."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    
    assert result["commits"] == 6
    assert result["author"]["email"] == "author_a@example.com"
    assert result["author"]["name"] == "Author A"
    
    # Check insertions/deletions are counted
    assert result["insertions"] > 0
    assert result["deletions"] >= 0


def test_summarize_author_contrib_share_percentage(multi_author_repo):
    """Test share of commits percentage calculation."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Author A has 6 out of 10 commits = 60%
    result_a = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    assert abs(result_a["share_of_commits_pct"] - 60.0) < 0.1
    
    # Author B has 4 out of 10 commits = 40%
    result_b = summarize_author_contrib(multi_author_repo, "author_b@example.com")
    assert abs(result_b["share_of_commits_pct"] - 40.0) < 0.1


def test_summarize_author_contrib_files_touched(multi_author_repo):
    """Test files touched count."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Author A touched: module1.py, auth.py, test_auth.py, README.md = 4 files
    result_a = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    assert result_a["files_touched"] == 4
    
    # Author B touched: dashboard.py, widget.py, test_widget.py = 3 files
    result_b = summarize_author_contrib(multi_author_repo, "author_b@example.com")
    assert result_b["files_touched"] == 3


def test_summarize_author_contrib_active_weeks(multi_author_repo):
    """Test active weeks count."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Author A has commits spanning multiple weeks
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    assert result["active_weeks"] >= 2


def test_summarize_author_contrib_activity_mix(multi_author_repo):
    """Test activity mix classification for author."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Author A: feat:2, fix:1, test:1, refactor:1, docs:1
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    
    activity_mix = result["activity_mix"]
    assert activity_mix["feature"] == 2
    assert activity_mix["bugfix"] == 1
    assert activity_mix["test"] == 1
    assert activity_mix["refactor"] == 1
    assert activity_mix["docs"] == 1
    
    # Total should equal author's commits
    total_classified = sum(activity_mix.values())
    assert total_classified == result["commits"]


def test_summarize_author_contrib_date_range(multi_author_repo):
    """Test first and last commit dates."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    
    assert "first_commit_at" in result
    assert "last_commit_at" in result
    
    # Validate date format YYYY-MM-DD
    first = result["first_commit_at"]
    last = result["last_commit_at"]
    assert len(first.split("-")) == 3
    assert len(last.split("-")) == 3
    
    # First should be <= last
    assert first <= last


def test_summarize_author_contrib_top_files(multi_author_repo):
    """Test top files touched by author."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Author A touched module1.py 3 times (initial + fix + refactor)
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    
    top_files = result["top_files"]
    assert len(top_files) > 0
    assert len(top_files) <= 10  # Should cap at 10
    
    # Each file entry should have path and touches
    for file_info in top_files:
        assert "path" in file_info
        assert "touches" in file_info
        assert file_info["touches"] > 0
    
    # Should be sorted by touches (descending)
    touches = [f["touches"] for f in top_files]
    assert touches == sorted(touches, reverse=True)
    
    # module1.py should be the most touched
    assert top_files[0]["path"] == "module1.py"
    assert top_files[0]["touches"] == 3


def test_summarize_author_contrib_fuzzy_match_by_name(multi_author_repo):
    """Test fuzzy matching by author name."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Match by partial name
    result = summarize_author_contrib(
        multi_author_repo,
        "Author A",
        prefer_email=False,
        fuzzy=True
    )
    
    assert result["commits"] == 6
    assert result["author"]["name"] == "Author A"


def test_summarize_author_contrib_fuzzy_match_substring(multi_author_repo):
    """Test fuzzy matching with substring."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Match by substring of email
    result = summarize_author_contrib(
        multi_author_repo,
        "author_a",
        fuzzy=True
    )
    
    assert result["commits"] == 6
    assert "author_a@example.com" in result["author"]["email"]


def test_summarize_author_contrib_case_insensitive(multi_author_repo):
    """Test case-insensitive matching."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    # Match with different case
    result = summarize_author_contrib(
        multi_author_repo,
        "AUTHOR_A@EXAMPLE.COM",
        fuzzy=True
    )
    
    assert result["commits"] == 6


def test_summarize_author_contrib_all_fields_present(multi_author_repo):
    """Test that all required fields are present in result."""
    from src.git.individual_contrib_analyzer import summarize_author_contrib
    
    result = summarize_author_contrib(multi_author_repo, "author_a@example.com")
    
    # Check all required fields
    required_fields = [
        "author", "commits", "insertions", "deletions",
        "files_touched", "active_weeks", "first_commit_at",
        "last_commit_at", "activity_mix", "share_of_commits_pct",
        "top_files"
    ]
    
    for field in required_fields:
        assert field in result, f"Missing field: {field}"
    
    # Check author sub-fields
    assert "name" in result["author"]
    assert "email" in result["author"]



