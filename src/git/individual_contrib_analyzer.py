"""
Individual contributor Git analyzer.
Provides per-author metrics and contribution analysis.
"""
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime

from ._git_utils import iter_commits, classify_intent, iso_week_start


def summarize_author_contrib(
    repo_path: Path,
    author_identifier: str,
    prefer_email: bool = True,
    fuzzy: bool = True
) -> Dict:
    """
    Summarize contributions for a specific author.
    
    Args:
        repo_path: Path to the Git repository
        author_identifier: Email (preferred) or name fragment to identify author
        prefer_email: If True, prioritize email matching over name
        fuzzy: If True, enable case-insensitive substring matching
    
    Returns:
        Dictionary containing:
            - author: Dict with "name" and "email"
            - commits: int - number of commits by this author
            - insertions: int - total lines inserted
            - deletions: int - total lines deleted
            - files_touched: int - number of unique files modified
            - active_weeks: int - number of distinct ISO weeks with commits
            - first_commit_at: str - date of first commit (YYYY-MM-DD)
            - last_commit_at: str - date of last commit (YYYY-MM-DD)
            - activity_mix: Dict[str, int] - commit counts by intent type
            - share_of_commits_pct: float - percentage of total repo commits
            - top_files: List[Dict] - up to 10 most-touched files
                Each file dict: {"path": str, "touches": int}
    """
    repo_path = Path(repo_path)
    
    # First pass: identify the target author and count total commits
    all_commits = list(iter_commits(repo_path))
    total_repo_commits = len(all_commits)
    
    target_author = _identify_author(all_commits, author_identifier, prefer_email, fuzzy)
    
    if not target_author:
        # Return empty result if author not found
        return _empty_author_result(author_identifier)
    
    target_name, target_email = target_author
    
    # Second pass: collect author's contributions
    author_commits = 0
    total_insertions = 0
    total_deletions = 0
    files_counter = Counter()  # file path -> touch count
    activity_mix = Counter()  # intent -> count
    active_weeks = set()
    first_commit_date = None
    last_commit_date = None
    
    for commit in all_commits:
        # Check if this commit belongs to target author
        if not _is_target_author(commit, target_name, target_email, fuzzy):
            continue
        
        author_commits += 1
        total_insertions += commit["insertions"]
        total_deletions += commit["deletions"]
        
        # Track files
        for file_path in commit["files"]:
            files_counter[file_path] += 1
        
        # Track commit date
        commit_date = commit["date"]
        if first_commit_date is None or commit_date < first_commit_date:
            first_commit_date = commit_date
        if last_commit_date is None or commit_date > last_commit_date:
            last_commit_date = commit_date
        
        # Track activity mix
        intent = classify_intent(commit["msg"])
        activity_mix[intent] += 1
        
        # Track active weeks
        week_start = iso_week_start(commit_date)
        active_weeks.add(week_start)
    
    # Calculate metrics
    files_touched = len(files_counter)
    active_weeks_count = len(active_weeks)
    
    share_pct = (author_commits / total_repo_commits * 100.0) if total_repo_commits > 0 else 0.0
    
    # Format dates
    first_commit_str = first_commit_date.date().isoformat() if first_commit_date else ""
    last_commit_str = last_commit_date.date().isoformat() if last_commit_date else ""
    
    # Top files (up to 10)
    top_files_list = [
        {"path": path, "touches": count}
        for path, count in files_counter.most_common(10)
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
        "author": {
            "name": target_name,
            "email": target_email,
        },
        "commits": author_commits,
        "insertions": total_insertions,
        "deletions": total_deletions,
        "files_touched": files_touched,
        "active_weeks": active_weeks_count,
        "first_commit_at": first_commit_str,
        "last_commit_at": last_commit_str,
        "activity_mix": activity_mix_dict,
        "share_of_commits_pct": share_pct,
        "top_files": top_files_list,
    }


def _identify_author(
    all_commits: List[Dict],
    author_identifier: str,
    prefer_email: bool,
    fuzzy: bool
) -> Optional[tuple]:
    """
    Identify the target author from commits based on identifier.
    
    Returns:
        Tuple of (name, email) or None if not found
    """
    identifier_lower = author_identifier.lower() if fuzzy else author_identifier
    
    # First try exact email match (case-insensitive if fuzzy)
    for commit in all_commits:
        email = commit["author_email"]
        if fuzzy:
            if email.lower() == identifier_lower:
                return (commit["author_name"], email)
        else:
            if email == author_identifier:
                return (commit["author_name"], email)
    
    # If fuzzy matching enabled, try substring matches
    if fuzzy:
        # Collect all unique authors with match scores
        author_matches = Counter()  # (name, email) -> match count
        
        for commit in all_commits:
            name = commit["author_name"]
            email = commit["author_email"]
            author_key = (name, email)
            
            # Check if identifier is substring of email or name
            if prefer_email:
                if identifier_lower in email.lower():
                    author_matches[author_key] += 1
                elif identifier_lower in name.lower():
                    author_matches[author_key] += 0.5  # Lower weight for name match
            else:
                if identifier_lower in name.lower():
                    author_matches[author_key] += 1
                elif identifier_lower in email.lower():
                    author_matches[author_key] += 0.5  # Lower weight for email match
        
        # Return author with most matches
        if author_matches:
            best_match = author_matches.most_common(1)[0][0]
            return best_match
    
    return None


def _is_target_author(commit: Dict, target_name: str, target_email: str, fuzzy: bool) -> bool:
    """
    Check if a commit belongs to the target author.
    
    Args:
        commit: Commit dictionary
        target_name: Target author name
        target_email: Target author email
        fuzzy: If True, use case-insensitive comparison
    
    Returns:
        True if commit is by target author
    """
    if fuzzy:
        return (
            commit["author_email"].lower() == target_email.lower() or
            (commit["author_name"].lower() == target_name.lower() and
             commit["author_email"].lower() == target_email.lower())
        )
    else:
        return (
            commit["author_email"] == target_email and
            commit["author_name"] == target_name
        )


def _empty_author_result(author_identifier: str) -> Dict:
    """
    Return an empty result structure when author is not found.
    
    Args:
        author_identifier: The identifier that was searched for
    
    Returns:
        Empty result dictionary
    """
    return {
        "author": {
            "name": "",
            "email": author_identifier,
        },
        "commits": 0,
        "insertions": 0,
        "deletions": 0,
        "files_touched": 0,
        "active_weeks": 0,
        "first_commit_at": "",
        "last_commit_at": "",
        "activity_mix": {
            "feature": 0,
            "bugfix": 0,
            "refactor": 0,
            "docs": 0,
            "test": 0,
            "other": 0,
        },
        "share_of_commits_pct": 0.0,
        "top_files": [],
    }



