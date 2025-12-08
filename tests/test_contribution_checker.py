import os
from pathlib import Path
from git import Repo, Actor
import pytest

from contributions.contribution_check import find_git_repos, get_commit_contributions


def create_git_repo(path: Path, commits=0, author="Test User <test@example.com>"):
    """
    Creates a real git repo with a specified number of commits and author.
    """
    repo = Repo.init(path)

    # Set a consistent author
    name, email = author.split(" <")
    email = email[:-1]

    with repo.config_writer() as cw:
        cw.set_value("user", "name", name)
        cw.set_value("user", "email", email)

    for i in range(commits):
        file_path = path / f"file{i}.txt"
        file_path.write_text(f"Commit {i}")

        repo.index.add([str(file_path)])
        repo.index.commit(f"Commit {i}")

    return repo


def test_find_git_repos_finds_repo(tmp_path):
    """
    Should detect directories that contain a .git folder.
    """
    repo_dir = tmp_path / "student" / "project"
    repo_dir.mkdir(parents=True)

    Repo.init(repo_dir)

    repos = find_git_repos(tmp_path)

    assert repo_dir in repos
    assert len(repos) == 1


def test_find_git_repos_ignores_non_repos(tmp_path):
    """
    Should not detect directories without .git.
    """
    non_repo = tmp_path / "folderA"
    non_repo.mkdir()

    repos = find_git_repos(tmp_path)

    assert repos == []


def test_get_commit_contributions_counts(tmp_path):
    """
    Should return correct commit counts for a single author.
    """
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()

    create_git_repo(repo_dir, commits=3, author="Alice <alice@example.com>")

    contributions = get_commit_contributions(repo_dir)

    assert contributions["Alice <alice@example.com>"] == 3


def test_multiple_authors(tmp_path):
    """
    Should count commits for multiple authors independently.
    """
    repo_dir = tmp_path / "repo2"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)

    alice = Actor("Alice", "alice@example.com")
    bob = Actor("Bob", "bob@example.com")

    # Author A commit
    file_a = repo_dir / "a.txt"
    file_a.write_text("A1")
    repo.index.add([str(file_a)])
    repo.index.commit("A commit", author=alice, committer=alice)

    # Author B commit
    file_b = repo_dir / "b.txt"
    file_b.write_text("B1")
    repo.index.add([str(file_b)])
    repo.index.commit("B commit", author=bob, committer=bob)

    contributions = get_commit_contributions(repo_dir)

    assert contributions["Alice <alice@example.com>"] == 1
    assert contributions["Bob <bob@example.com>"] == 1