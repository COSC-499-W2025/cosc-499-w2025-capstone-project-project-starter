"""
ProjectInfo aggregator: merges metrics from local and git analyzers into a single rank-aware JSON.
"""
import argparse
import datetime
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal, Optional


@dataclass
class ProjectInfo:
    """Canonical project metadata with rank-aware fields."""
    id: str
    name: str
    source: Literal["local", "git", "merged"]
    duration: dict  # {"start": str|None, "end": str|None, "days": int}
    is_collaborative: bool
    authors: list  # [{"name","email","commits"}]
    languages: list
    frameworks: list
    skills: list
    activity_mix: dict  # {"code": int, "test": int, "doc": int}
    lines_of_code: int
    totals: dict  # {"files": int, "commits": int}
    notes: list
    rank_inputs: dict
    preliminary_score: float


# Extension to language name mapping
EXT_TO_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".java": "Java",
    ".ts": "TypeScript",
    ".cpp": "C++",
    ".c": "C",
    ".rb": "Ruby",
    ".go": "Go",
    ".rs": "Rust",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".cs": "C#",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
}


def _safe_get(d: dict, key: str, default=None):
    """Safely get a value from dict."""
    return d.get(key, default) if d else default


def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """Parse ISO date string, ignoring timezone."""
    if not date_str:
        return None
    try:
        # Handle ISO format with or without time/timezone
        date_part = date_str.split('T')[0]
        return datetime.date.fromisoformat(date_part)
    except (ValueError, AttributeError):
        return None


def _compute_id(name: str, source: str, end: Optional[str]) -> str:
    """Generate stable ID from name, source, and end date."""
    key = f"{name.lower()}|{source}|{end or ''}"
    return hashlib.sha1(key.encode()).hexdigest()


def _normalize_languages(lang_data) -> list:
    """Normalize language data to list of strings."""
    if not lang_data:
        return []
    
    if isinstance(lang_data, list):
        if not lang_data:
            return []
        # Check if it's a list of dicts with "ext" key
        if isinstance(lang_data[0], dict) and "ext" in lang_data[0]:
            result = []
            for item in lang_data:
                ext = item.get("ext", "")
                lang = EXT_TO_LANG.get(ext, ext.lstrip('.').capitalize() if ext else "Unknown")
                if lang not in result:
                    result.append(lang)
            return result
        # Already a list of strings
        return [str(x) for x in lang_data]
    
    return []


def _union_lists(list1: list, list2: list) -> list:
    """Union of two lists, case-insensitive, preserving first occurrence casing."""
    result = []
    seen_lower = set()
    
    for item in list1 + list2:
        item_str = str(item)
        lower = item_str.lower()
        if lower not in seen_lower:
            seen_lower.add(lower)
            result.append(item_str)
    
    return result


def compute_rank_inputs(pi: ProjectInfo) -> dict:
    """Compute rank inputs from ProjectInfo fields."""
    loc = pi.lines_of_code
    commits = pi.totals.get("commits", 0)
    skills_breadth = len(pi.skills)
    
    # Compute recency_days
    end_str = pi.duration.get("end")
    recency_days = 0
    if end_str:
        end_date = _parse_iso_date(end_str)
        if end_date:
            today = datetime.date.today()
            recency_days = max(0, (today - end_date).days)
    
    is_collab = 1 if pi.is_collaborative else 0
    
    # Compute code_frac
    code = pi.activity_mix.get("code", 0)
    test = pi.activity_mix.get("test", 0)
    doc = pi.activity_mix.get("doc", 0)
    total_activity = code + test + doc
    code_frac = code / max(1, total_activity) if total_activity > 0 else 0.0
    
    return {
        "loc": loc,
        "commits": commits,
        "skills_breadth": skills_breadth,
        "recency_days": recency_days,
        "is_collab": is_collab,
        "code_frac": code_frac,
    }


def compute_preliminary_score(rank_inputs: dict) -> float:
    """Compute preliminary score from rank inputs."""
    loc = rank_inputs.get("loc", 0)
    commits = rank_inputs.get("commits", 0)
    skills_breadth = rank_inputs.get("skills_breadth", 0)
    recency_days = rank_inputs.get("recency_days", 0)
    is_collab = rank_inputs.get("is_collab", 0)
    
    # Recency score
    if recency_days <= 180:
        recency_score = 1.0
    elif recency_days <= 365:
        recency_score = 0.5
    else:
        recency_score = 0.1
    
    score = (
        0.35 * math.log1p(loc) +
        0.35 * math.log1p(commits) +
        0.20 * skills_breadth +
        0.10 * recency_score +
        0.05 * is_collab
    )
    
    return round(score, 4)


def from_local(root_dir: str, local_metrics: dict) -> ProjectInfo:
    """Create ProjectInfo from local analyzer metrics."""
    name = Path(root_dir).name
    
    # Extract fields with defaults
    languages = _safe_get(local_metrics, "languages", [])
    frameworks = _safe_get(local_metrics, "frameworks", [])
    skills = _safe_get(local_metrics, "skills", [])
    lines_of_code = _safe_get(local_metrics, "lines_of_code", 0)
    activity_mix = _safe_get(local_metrics, "activity_mix", {"code": 0, "test": 0, "doc": 0})
    
    # Duration
    duration_data = _safe_get(local_metrics, "duration", {})
    duration = {
        "start": _safe_get(duration_data, "start"),
        "end": _safe_get(duration_data, "end"),
        "days": _safe_get(duration_data, "days", 0),
    }
    
    # Totals
    totals_data = _safe_get(local_metrics, "totals", {})
    totals = {
        "files": _safe_get(totals_data, "files", 0),
        "commits": 0,
    }
    
    notes = _safe_get(local_metrics, "notes", [])
    if not isinstance(notes, list):
        notes = []
    
    # Create ProjectInfo with placeholder rank_inputs and score
    pi = ProjectInfo(
        id="",  # Will be computed after
        name=name,
        source="local",
        duration=duration,
        is_collaborative=False,
        authors=[],
        languages=languages,
        frameworks=frameworks,
        skills=skills,
        activity_mix=activity_mix,
        lines_of_code=lines_of_code,
        totals=totals,
        notes=notes,
        rank_inputs={},
        preliminary_score=0.0,
    )
    
    # Compute rank inputs and score
    pi.rank_inputs = compute_rank_inputs(pi)
    pi.preliminary_score = compute_preliminary_score(pi.rank_inputs)
    pi.id = _compute_id(pi.name, pi.source, pi.duration.get("end"))
    
    return pi


def from_git(repo_path: str, git_metrics: dict) -> ProjectInfo:
    """Create ProjectInfo from git analyzer metrics."""
    name = Path(repo_path).name
    
    # Authors
    authors = _safe_get(git_metrics, "authors", [])
    if not isinstance(authors, list):
        authors = []
    
    # Is collaborative
    is_collaborative = _safe_get(git_metrics, "is_collaborative")
    if is_collaborative is None:
        is_collaborative = len(authors) > 1
    
    # Duration - normalize keys
    duration_data = _safe_get(git_metrics, "duration", {})
    start = _safe_get(duration_data, "first_commit_iso") or _safe_get(duration_data, "start")
    end = _safe_get(duration_data, "last_commit_iso") or _safe_get(duration_data, "end")
    days = _safe_get(duration_data, "days", 0)
    
    duration = {
        "start": start,
        "end": end,
        "days": days,
    }
    
    # Commits
    commits = _safe_get(git_metrics, "commits", 0)
    
    # Files
    files_touched = _safe_get(git_metrics, "files_touched", 0)
    
    # Activity mix
    by_activity = _safe_get(git_metrics, "by_activity", {})
    activity_mix = {
        "code": _safe_get(by_activity, "code", 0),
        "test": _safe_get(by_activity, "test", 0),
        "doc": _safe_get(by_activity, "doc", 0),
    }
    
    # Languages - normalize
    lang_data = _safe_get(git_metrics, "languages", [])
    languages = _normalize_languages(lang_data)
    
    # Lines of code (optional from git)
    lines_of_code = _safe_get(git_metrics, "lines_of_code", 0)
    
    notes = _safe_get(git_metrics, "notes", [])
    if not isinstance(notes, list):
        notes = []
    
    totals = {
        "files": files_touched,
        "commits": commits,
    }
    
    # Create ProjectInfo
    pi = ProjectInfo(
        id="",
        name=name,
        source="git",
        duration=duration,
        is_collaborative=is_collaborative,
        authors=authors,
        languages=languages,
        frameworks=[],
        skills=[],
        activity_mix=activity_mix,
        lines_of_code=lines_of_code,
        totals=totals,
        notes=notes,
        rank_inputs={},
        preliminary_score=0.0,
    )
    
    # Compute rank inputs and score
    pi.rank_inputs = compute_rank_inputs(pi)
    pi.preliminary_score = compute_preliminary_score(pi.rank_inputs)
    pi.id = _compute_id(pi.name, pi.source, pi.duration.get("end"))
    
    return pi


def merge_local_git(local_pi: ProjectInfo, git_pi: ProjectInfo) -> ProjectInfo:
    """Merge local and git ProjectInfo into a single merged ProjectInfo."""
    # Name: prefer git if present
    name = git_pi.name if git_pi.name else local_pi.name
    
    # Duration: prefer git, but compute wider span if both present
    duration = git_pi.duration.copy()
    if not duration.get("start") and local_pi.duration.get("start"):
        duration = local_pi.duration.copy()
    elif duration.get("start") and local_pi.duration.get("start"):
        # Both have duration - take wider span
        git_start = _parse_iso_date(git_pi.duration.get("start"))
        git_end = _parse_iso_date(git_pi.duration.get("end"))
        local_start = _parse_iso_date(local_pi.duration.get("start"))
        local_end = _parse_iso_date(local_pi.duration.get("end"))
        
        start_dates = [d for d in [git_start, local_start] if d]
        end_dates = [d for d in [git_end, local_end] if d]
        
        if start_dates and end_dates:
            final_start = min(start_dates)
            final_end = max(end_dates)
            duration = {
                "start": final_start.isoformat(),
                "end": final_end.isoformat(),
                "days": (final_end - final_start).days,
            }
    
    # Authors and is_collaborative from git
    authors = git_pi.authors
    is_collaborative = git_pi.is_collaborative
    
    # Union of languages, frameworks, skills
    languages = _union_lists(local_pi.languages, git_pi.languages)
    frameworks = _union_lists(local_pi.frameworks, git_pi.frameworks)
    skills = _union_lists(local_pi.skills, git_pi.skills)
    
    # Activity mix: prefer git if present
    activity_mix = git_pi.activity_mix.copy()
    if sum(activity_mix.values()) == 0:
        activity_mix = local_pi.activity_mix.copy()
    
    # Lines of code: prefer local if > 0
    lines_of_code = local_pi.lines_of_code if local_pi.lines_of_code > 0 else git_pi.lines_of_code
    
    # Totals: max files, git commits
    totals = {
        "files": max(local_pi.totals.get("files", 0), git_pi.totals.get("files", 0)),
        "commits": git_pi.totals.get("commits", 0),
    }
    
    # Notes: concatenate and dedupe
    notes = _union_lists(local_pi.notes, git_pi.notes)
    
    # Create merged ProjectInfo
    pi = ProjectInfo(
        id="",
        name=name,
        source="merged",
        duration=duration,
        is_collaborative=is_collaborative,
        authors=authors,
        languages=languages,
        frameworks=frameworks,
        skills=skills,
        activity_mix=activity_mix,
        lines_of_code=lines_of_code,
        totals=totals,
        notes=notes,
        rank_inputs={},
        preliminary_score=0.0,
    )
    
    # Recompute rank inputs and score
    pi.rank_inputs = compute_rank_inputs(pi)
    pi.preliminary_score = compute_preliminary_score(pi.rank_inputs)
    pi.id = _compute_id(pi.name, pi.source, pi.duration.get("end"))
    
    return pi


def to_dict(pi: ProjectInfo) -> dict:
    """Convert ProjectInfo to dictionary."""
    return asdict(pi)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Aggregate project metrics into rank-aware JSON"
    )
    parser.add_argument(
        "--from",
        dest="mode",
        required=True,
        choices=["local", "git", "merge"],
        help="Aggregation mode",
    )
    parser.add_argument("--root", help="Root directory for local mode")
    parser.add_argument("--metrics", help="Metrics JSON file for local/git mode")
    parser.add_argument("--repo", help="Repository path for git mode")
    parser.add_argument("--local-metrics", help="Local metrics JSON for merge mode")
    parser.add_argument("--git-metrics", help="Git metrics JSON for merge mode")
    
    args = parser.parse_args()
    
    try:
        if args.mode == "local":
            if not args.root or not args.metrics:
                print("Error: --root and --metrics required for local mode", file=sys.stderr)
                sys.exit(1)
            
            with open(args.metrics, 'r') as f:
                local_metrics = json.load(f)
            
            pi = from_local(args.root, local_metrics)
            print(json.dumps(to_dict(pi), indent=2))
        
        elif args.mode == "git":
            if not args.repo or not args.metrics:
                print("Error: --repo and --metrics required for git mode", file=sys.stderr)
                sys.exit(1)
            
            with open(args.metrics, 'r') as f:
                git_metrics = json.load(f)
            
            pi = from_git(args.repo, git_metrics)
            print(json.dumps(to_dict(pi), indent=2))
        
        elif args.mode == "merge":
            if not args.root or not args.local_metrics or not args.repo or not args.git_metrics:
                print("Error: --root, --local-metrics, --repo, and --git-metrics required for merge mode", file=sys.stderr)
                sys.exit(1)
            
            with open(args.local_metrics, 'r') as f:
                local_metrics = json.load(f)
            with open(args.git_metrics, 'r') as f:
                git_metrics = json.load(f)
            
            local_pi = from_local(args.root, local_metrics)
            git_pi = from_git(args.repo, git_metrics)
            merged_pi = merge_local_git(local_pi, git_pi)
            
            print(json.dumps(to_dict(merged_pi), indent=2))
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

