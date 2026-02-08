"""
Project-level Git repository analyzer.
Provides aggregate statistics about the repository without per-author focus.
"""
from pathlib import Path
from typing import Dict, List
from collections import Counter, defaultdict
from datetime import datetime

from ._git_utils import iter_commits, classify_intent, iso_week_start


def analyze_project_repo(repo_path: Path) -> Dict:
    """
    Analyze a Git repository and return project-level statistics.
    
    Args:
        repo_path: Path to the Git repository
    
    Returns:
        Dictionary containing:
            - repo_path: str - path to the repository
            - total_commits: int - total number of commits
            - unique_authors: int - number of unique authors
            - authors: List[Dict] - author details sorted by commit count
                Each author dict: {"name": str, "email": str, "commits": int}
            - first_commit_at: str - date of first commit (YYYY-MM-DD)
            - last_commit_at: str - date of last commit (YYYY-MM-DD)
            - duration_days: int - days between first and last commit
            - activity_mix: Dict[str, int] - commit counts by intent type
                Keys: "feature", "bugfix", "refactor", "docs", "test", "other"
            - weekly_activity: List[Dict] - commits per ISO week
                Each week dict: {"week_start": str (YYYY-MM-DD), "commits": int}
            - project_type: str - "individual" or "collaborative"
    """
    repo_path = Path(repo_path)
    
    # Initialize counters and aggregators
    total_commits = 0
    authors_counter = Counter()  # (name, email) -> count
    activity_mix = Counter()  # intent -> count
    weekly_activity = Counter()  # week_start -> count
    first_commit_date = None
    last_commit_date = None
    
    # Collect all commits
    for commit in iter_commits(repo_path):
        total_commits += 1
        
        # Track author
        author_key = (commit["author_name"], commit["author_email"])
        authors_counter[author_key] += 1
        
        # Track commit date for duration
        commit_date = commit["date"]
        if first_commit_date is None or commit_date < first_commit_date:
            first_commit_date = commit_date
        if last_commit_date is None or commit_date > last_commit_date:
            last_commit_date = commit_date
        
        # Classify intent
        intent = classify_intent(commit["msg"])
        activity_mix[intent] += 1
        
        # Weekly activity
        week_start = iso_week_start(commit_date)
        weekly_activity[week_start] += 1
    
    # Process authors
    unique_authors = len(authors_counter)
    authors_list = [
        {
            "name": name,
            "email": email,
            "commits": count
        }
        for (name, email), count in authors_counter.most_common()
    ]
    
    # Determine project type
    project_type = "collaborative" if unique_authors > 1 else "individual"
    
    # Calculate duration
    if first_commit_date and last_commit_date:
        duration_days = (last_commit_date.date() - first_commit_date.date()).days
        first_commit_str = first_commit_date.date().isoformat()
        last_commit_str = last_commit_date.date().isoformat()
    else:
        duration_days = 0
        first_commit_str = ""
        last_commit_str = ""
    
    # Format weekly activity
    weekly_activity_list = [
        {
            "week_start": week_start.isoformat(),
            "commits": count
        }
        for week_start, count in sorted(weekly_activity.items())
    ]
    
    # Ensure all activity_mix keys are present
    activity_mix_dict = {
        "feature": activity_mix.get("feature", 0),
        "bugfix": activity_mix.get("bugfix", 0),
        "refactor": activity_mix.get("refactor", 0),
        "docs": activity_mix.get("docs", 0),
        "test": activity_mix.get("test", 0),
        "other": activity_mix.get("other", 0),
    }
    
    return {
        "repo_path": str(repo_path),
        "total_commits": total_commits,
        "unique_authors": unique_authors,
        "authors": authors_list,
        "first_commit_at": first_commit_str,
        "last_commit_at": last_commit_str,
        "duration_days": duration_days,
        "activity_mix": activity_mix_dict,
        "weekly_activity": weekly_activity_list,
        "project_type": project_type,
    }

