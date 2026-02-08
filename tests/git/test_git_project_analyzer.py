"""
Tests for project-level Git analytics.
Creates a temporary Git repository and validates project-level metrics.
"""
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import pytest


@pytest.fixture
def temp_git_repo():
    """
    Create a temporary Git repo with 8 commits across 2 ISO weeks,
    alternating between two authors, with various commit message types.
    """
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Author A"],
            cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "author_a@example.com"],
            cwd=repo_path, check=True, capture_output=True
        )
        
        # Base date for commits (ensure we span at least 2 ISO weeks)
        # ISO week starts on Monday
        base_date = datetime(2024, 1, 1, 12, 0, 0)  # Monday, Jan 1, 2024
        
        commits_data = [
            # Week 1 - Author A
            ("author_a@example.com", "Author A", "feat: add initial structure", base_date, "file1.py"),
            # Week 1 - Author B
            ("author_b@example.com", "Author B", "fix: correct bug in structure", base_date + timedelta(days=1), "file1.py"),
            # Week 1 - Author A
            ("author_a@example.com", "Author A", "refactor: clean up code", base_date + timedelta(days=2), "file2.py"),
            # Week 1 - Author B
            ("author_b@example.com", "Author B", "docs: update README", base_date + timedelta(days=3), "README.md"),
            # Week 2 - Author A (at least 7 days later)
            ("author_a@example.com", "Author A", "test: add unit tests", base_date + timedelta(days=8), "test_file.py"),
            # Week 2 - Author B
            ("author_b@example.com", "Author B", "feat: implement new feature", base_date + timedelta(days=9), "file3.py"),
            # Week 2 - Author A
            ("author_a@example.com", "Author A", "fix: resolve edge case", base_date + timedelta(days=10), "file1.py"),
            # Week 2 - Author B
            ("author_b@example.com", "Author B", "add more functionality", base_date + timedelta(days=11), "file4.py"),
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
            
            # Create/modify file
            file_path = repo_path / filename
            with open(file_path, "a") as f:
                f.write(f"# Content added at {commit_date}\n")
                f.write(f"# {message}\n\n")
            
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


def test_analyze_project_repo_basic_stats(temp_git_repo):
    """Test basic project statistics."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    assert result["total_commits"] == 8
    assert result["unique_authors"] == 2
    assert result["project_type"] == "collaborative"
    assert len(result["authors"]) == 2
    
    # Check authors are sorted by commit count
    assert result["authors"][0]["commits"] >= result["authors"][1]["commits"]


def test_analyze_project_repo_duration(temp_git_repo):
    """Test project duration calculation."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    assert result["duration_days"] > 0
    assert result["duration_days"] >= 10  # Our commits span at least 11 days
    assert "first_commit_at" in result
    assert "last_commit_at" in result
    
    # Validate date format YYYY-MM-DD
    first = result["first_commit_at"]
    last = result["last_commit_at"]
    assert len(first.split("-")) == 3
    assert len(last.split("-")) == 3


def test_analyze_project_repo_activity_mix(temp_git_repo):
    """Test activity mix classification."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    activity_mix = result["activity_mix"]
    
    # We have commits with: feat:, fix:, refactor:, docs:, test:, and one without prefix
    assert activity_mix["feature"] >= 2  # "feat:" prefix
    assert activity_mix["bugfix"] >= 2   # "fix:" prefix
    assert activity_mix["refactor"] >= 1
    assert activity_mix["docs"] >= 1
    assert activity_mix["test"] >= 1
    assert activity_mix["other"] >= 0   # The "add more functionality" commit
    
    # Total should equal commit count
    total_classified = sum(activity_mix.values())
    assert total_classified == result["total_commits"]


def test_analyze_project_repo_weekly_activity(temp_git_repo):
    """Test weekly activity bucketing."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    weekly_activity = result["weekly_activity"]
    
    # Should have at least 2 weeks
    assert len(weekly_activity) >= 2
    
    # Each week entry should have correct format
    for week in weekly_activity:
        assert "week_start" in week
        assert "commits" in week
        assert week["commits"] > 0
        # Validate date format
        assert len(week["week_start"].split("-")) == 3
    
    # Total commits across weeks should match
    total_commits = sum(w["commits"] for w in weekly_activity)
    assert total_commits == result["total_commits"]


def test_analyze_project_repo_authors_detail(temp_git_repo):
    """Test detailed author information."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    authors = result["authors"]
    
    # Each author should have required fields
    for author in authors:
        assert "name" in author
        assert "email" in author
        assert "commits" in author
        assert author["commits"] > 0
        assert "@example.com" in author["email"]
    
    # Check both authors present
    emails = {a["email"] for a in authors}
    assert "author_a@example.com" in emails
    assert "author_b@example.com" in emails


def test_analyze_project_repo_individual_project():
    """Test project_type detection for individual project."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    # Create a single-author repo
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    try:
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Solo Dev"],
            cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "solo@example.com"],
            cwd=repo_path, check=True, capture_output=True
        )
        
        # Create a single commit
        file_path = repo_path / "file.txt"
        file_path.write_text("content")
        subprocess.run(["git", "add", "file.txt"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True)
        
        result = analyze_project_repo(repo_path)
        
        assert result["project_type"] == "individual"
        assert result["unique_authors"] == 1
        assert result["total_commits"] == 1
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_analyze_project_repo_path_in_result(temp_git_repo):
    """Test that repo_path is included in result."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(temp_git_repo)
    
    assert "repo_path" in result
    assert str(temp_git_repo) in result["repo_path"]

