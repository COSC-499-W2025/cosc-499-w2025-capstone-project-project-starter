"""
Test that Git analytics work with both PyDriller and GitPython backends.
"""
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import pytest


@pytest.fixture
def simple_git_repo():
    """Create a minimal Git repo for backend testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test Author"],
            cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path, check=True, capture_output=True
        )
        
        # Create a commit
        file_path = repo_path / "test.txt"
        file_path.write_text("Hello World\n")
        subprocess.run(["git", "add", "test.txt"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: initial commit"], cwd=repo_path, check=True, capture_output=True)
        
        yield repo_path
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_gitpython_backend_available():
    """Test that GitPython is available and works."""
    try:
        from git import Repo as GitRepo
        assert GitRepo is not None
        print("GitPython is available")
    except ImportError:
        pytest.skip("GitPython not installed")


def test_iter_commits_works_with_available_backend(simple_git_repo):
    """Test that iter_commits works with whichever backend is available."""
    from src.git._git_utils import iter_commits
    
    commits = list(iter_commits(simple_git_repo))
    
    assert len(commits) > 0
    commit = commits[0]
    
    # Verify commit structure
    assert "author_name" in commit
    assert "author_email" in commit
    assert "msg" in commit
    assert "date" in commit
    assert "insertions" in commit
    assert "deletions" in commit
    assert "files" in commit
    
    assert commit["author_email"] == "test@example.com"
    assert "feat:" in commit["msg"]


def test_backend_detection():
    """Test that we correctly detect which backend is available."""
    from src.git import _git_utils
    
    # At least one should be available based on requirements.txt
    assert _git_utils.PYDRILLER_AVAILABLE or _git_utils.GITPYTHON_AVAILABLE
    
    if _git_utils.PYDRILLER_AVAILABLE:
        print("Using PyDriller backend")
        assert _git_utils.Repository is not None
    
    if _git_utils.GITPYTHON_AVAILABLE:
        print("GitPython backend available as fallback")
        assert _git_utils.GitRepo is not None


def test_project_analyzer_works_with_backend(simple_git_repo):
    """Test that project analyzer works with available backend."""
    from src.git.project_git_analyzer import analyze_project_repo
    
    result = analyze_project_repo(simple_git_repo)
    
    assert result["total_commits"] == 1
    assert result["unique_authors"] == 1
    assert result["project_type"] == "individual"
    assert len(result["authors"]) == 1
    assert result["authors"][0]["email"] == "test@example.com"

