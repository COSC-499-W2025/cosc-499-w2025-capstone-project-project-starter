import os
from pathlib import Path
from git import Repo  # GitPython


def find_git_repos(directory):
    """
    Recursively finds directories that contain a .git folder.
    Returns a list of absolute paths to detected git repositories.
    """
    directory = Path(directory)
    git_repos = []

    for root, dirs, _files in os.walk(directory):
        root_path = Path(root)
        if ".git" in dirs:
            git_repos.append(root_path)

    return git_repos


def get_commit_contributions(repo_path):
    """
    Returns a dictionary of commit counts per author in the given repo.
    Key: "Name <email>"
    Value: commit count
    """
    repo = Repo(repo_path)
    contributions = {}

    for commit in repo.iter_commits():
        author = f"{commit.author.name} <{commit.author.email}>"
        contributions[author] = contributions.get(author, 0) + 1

    return contributions
