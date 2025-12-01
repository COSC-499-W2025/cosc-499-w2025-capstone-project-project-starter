import pytest
from unittest.mock import patch, MagicMock

from contributions.contribution_checker import (
    is_git_repo,
    get_github_repo_url,
    get_user_commit_count,
)

# ------------------------------
# is_git_repo()
# ------------------------------

@patch("os.path.isdir")
def test_is_git_repo_true(mock_isdir):
    mock_isdir.return_value = True
    assert is_git_repo("/path/project") is True


@patch("os.path.isdir")
def test_is_git_repo_false(mock_isdir):
    mock_isdir.return_value = False
    assert is_git_repo("/path/project") is False


# ------------------------------
# get_github_repo_url()
# ------------------------------

@patch("subprocess.check_output")
def test_get_github_repo_url_success(mock_check_output):
    mock_check_output.return_value = b"https://github.com/user/repo.git\n"
    url = get_github_repo_url("/path/project")
    assert url == "https://github.com/user/repo"


@patch("subprocess.check_output", side_effect=Exception("git error"))
def test_get_github_repo_url_failure(_):
    assert get_github_repo_url("/path/project") is None


# ------------------------------
# get_user_commit_count()
# ------------------------------

@patch("requests.get")
def test_get_user_commit_count_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"commit": {"author": {"email": "me@example.com"}}},
        {"commit": {"author": {"email": "someone@example.com"}}},
        {"commit": {"author": {"email": "me@example.com"}}},
    ]
    mock_get.return_value = mock_resp

    count = get_user_commit_count("user", "repo", "me@example.com")
    assert count == 2


@patch("requests.get")
def test_get_user_commit_count_github_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    count = get_user_commit_count("user", "repo", "me@example.com")
    assert count is None


@patch("requests.get", side_effect=Exception("network fail"))
def test_get_user_commit_count_exception(_):
    count = get_user_commit_count("user", "repo", "me@example.com")
    assert count is None
