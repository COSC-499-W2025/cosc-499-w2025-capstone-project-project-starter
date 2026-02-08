"""
Tests for project aggregator functionality.
"""
import pytest
from src.project.aggregator import (
    ProjectInfo,
    from_local,
    from_git,
    merge_local_git,
    compute_rank_inputs,
    compute_preliminary_score,
    to_dict,
)


def test_from_local_minimal():
    """Test creating ProjectInfo from minimal local metrics."""
    local_metrics = {
        "lines_of_code": 1500,
        "activity_mix": {"code": 100, "test": 20, "doc": 10},
        "skills": ["Python", "Git", "Testing"],
        "languages": ["Python"],
        "frameworks": ["Flask"],
    }
    
    pi = from_local("/path/to/project", local_metrics)
    
    # Basic fields
    assert pi.name == "project"
    assert pi.source == "local"
    assert pi.lines_of_code == 1500
    assert pi.skills == ["Python", "Git", "Testing"]
    assert pi.is_collaborative is False
    assert pi.authors == []
    
    # Rank inputs
    assert pi.rank_inputs["loc"] == 1500
    assert pi.rank_inputs["skills_breadth"] == 3
    assert pi.rank_inputs["recency_days"] >= 0
    assert pi.rank_inputs["is_collab"] == 0
    
    # Code fraction
    code_frac = pi.rank_inputs["code_frac"]
    assert code_frac > 0.7  # 100 / 130
    
    # Preliminary score
    assert pi.preliminary_score > 0


def test_from_git_minimal():
    """Test creating ProjectInfo from minimal git metrics."""
    git_metrics = {
        "authors": [
            {"name": "Alice", "email": "alice@example.com", "commits": 50},
            {"name": "Bob", "email": "bob@example.com", "commits": 30},
        ],
        "commits": 80,
        "by_activity": {"code": 60, "test": 15, "doc": 5},
        "duration": {
            "first_commit_iso": "2023-01-01",
            "last_commit_iso": "2023-12-31",
            "days": 364,
        },
        "files_touched": 45,
    }
    
    pi = from_git("/path/to/repo", git_metrics)
    
    # Basic fields
    assert pi.name == "repo"
    assert pi.source == "git"
    assert pi.is_collaborative is True
    assert len(pi.authors) == 2
    assert pi.totals["commits"] == 80
    
    # Rank inputs
    assert pi.rank_inputs["commits"] == 80
    assert pi.rank_inputs["commits"] > 0
    assert pi.rank_inputs["is_collab"] == 1
    
    # Duration normalized
    assert pi.duration["start"] == "2023-01-01"
    assert pi.duration["end"] == "2023-12-31"
    assert pi.duration["days"] == 364
    
    # Preliminary score
    assert pi.preliminary_score > 0


def test_merge_local_git():
    """Test merging local and git ProjectInfo."""
    local_metrics = {
        "lines_of_code": 2000,
        "activity_mix": {"code": 150, "test": 30, "doc": 20},
        "skills": ["Python", "Flask", "SQLAlchemy"],
        "languages": ["Python"],
        "frameworks": ["Flask"],
    }
    
    git_metrics = {
        "authors": [
            {"name": "Alice", "email": "alice@example.com", "commits": 100},
        ],
        "commits": 100,
        "by_activity": {"code": 80, "test": 15, "doc": 5},
        "duration": {
            "first_commit_iso": "2024-01-01",
            "last_commit_iso": "2024-11-01",
            "days": 305,
        },
        "files_touched": 50,
        "languages": [{"ext": ".py", "count": 45}, {"ext": ".js", "count": 5}],
    }
    
    local_pi = from_local("/path/to/project", local_metrics)
    git_pi = from_git("/path/to/project", git_metrics)
    merged_pi = merge_local_git(local_pi, git_pi)
    
    # Source is merged
    assert merged_pi.source == "merged"
    
    # Languages union (Python from both, JavaScript from git)
    assert "Python" in merged_pi.languages
    assert "JavaScript" in merged_pi.languages
    
    # Skills union
    assert "Python" in merged_pi.skills
    assert "Flask" in merged_pi.skills
    assert "SQLAlchemy" in merged_pi.skills
    
    # Lines of code from local (>0)
    assert merged_pi.lines_of_code == 2000
    
    # Commits from git
    assert merged_pi.totals["commits"] == 100
    
    # Is collaborative from git
    assert merged_pi.is_collaborative is False  # Only 1 author
    
    # Authors from git
    assert len(merged_pi.authors) == 1
    
    # Preliminary score computed
    assert merged_pi.preliminary_score > 0


def test_id_stability():
    """Test that same inputs produce same ID."""
    local_metrics = {
        "lines_of_code": 1000,
        "activity_mix": {"code": 100, "test": 20, "doc": 10},
        "skills": ["Python"],
        "languages": ["Python"],
        "duration": {"start": "2024-01-01", "end": "2024-12-01", "days": 335},
    }
    
    pi1 = from_local("/path/to/myproject", local_metrics)
    pi2 = from_local("/path/to/myproject", local_metrics)
    
    # Same inputs should produce same ID
    assert pi1.id == pi2.id
    assert pi1.id != ""
    
    # Different end date should produce different ID
    local_metrics_2 = local_metrics.copy()
    local_metrics_2["duration"] = {"start": "2024-01-01", "end": "2024-12-15", "days": 349}
    pi3 = from_local("/path/to/myproject", local_metrics_2)
    
    assert pi3.id != pi1.id


def test_compute_rank_inputs():
    """Test rank inputs computation."""
    local_metrics = {
        "lines_of_code": 5000,
        "activity_mix": {"code": 200, "test": 50, "doc": 50},
        "skills": ["Python", "JavaScript", "Docker", "PostgreSQL"],
        "languages": ["Python", "JavaScript"],
        "duration": {"start": "2024-01-01", "end": "2024-11-01", "days": 305},
    }
    
    pi = from_local("/path/to/project", local_metrics)
    rank_inputs = pi.rank_inputs
    
    assert rank_inputs["loc"] == 5000
    assert rank_inputs["commits"] == 0  # Local has no commits
    assert rank_inputs["skills_breadth"] == 4
    assert rank_inputs["recency_days"] >= 0
    assert rank_inputs["is_collab"] == 0
    
    # Code fraction: 200 / (200 + 50 + 50) = 200/300 = 0.666...
    assert 0.65 < rank_inputs["code_frac"] < 0.7


def test_preliminary_score_calculation():
    """Test preliminary score calculation."""
    rank_inputs = {
        "loc": 1000,
        "commits": 50,
        "skills_breadth": 3,
        "recency_days": 100,  # Recent (< 180 days)
        "is_collab": 1,
        "code_frac": 0.75,
    }
    
    score = compute_preliminary_score(rank_inputs)
    
    # Should be positive
    assert score > 0
    
    # Should be rounded to 4 decimal places
    assert len(str(score).split('.')[-1]) <= 4


def test_to_dict():
    """Test conversion to dictionary."""
    local_metrics = {
        "lines_of_code": 1000,
        "activity_mix": {"code": 100, "test": 20, "doc": 10},
        "skills": ["Python"],
        "languages": ["Python"],
    }
    
    pi = from_local("/path/to/project", local_metrics)
    pi_dict = to_dict(pi)
    
    # Should be a dict
    assert isinstance(pi_dict, dict)
    
    # Should have all required fields
    assert "id" in pi_dict
    assert "name" in pi_dict
    assert "source" in pi_dict
    assert "rank_inputs" in pi_dict
    assert "preliminary_score" in pi_dict


def test_git_language_normalization():
    """Test that git languages with extensions are normalized correctly."""
    git_metrics = {
        "authors": [{"name": "Alice", "email": "alice@example.com", "commits": 10}],
        "commits": 10,
        "by_activity": {"code": 10, "test": 0, "doc": 0},
        "languages": [
            {"ext": ".py", "count": 50},
            {"ext": ".js", "count": 30},
            {"ext": ".cpp", "count": 20},
            {"ext": ".unknown", "count": 5},
        ],
    }
    
    pi = from_git("/path/to/repo", git_metrics)
    
    assert "Python" in pi.languages
    assert "JavaScript" in pi.languages
    assert "C++" in pi.languages
    # Unknown extension should be capitalized without dot
    assert "Unknown" in pi.languages


def test_merge_duration_wider_span():
    """Test that merge uses wider span when both have durations."""
    local_metrics = {
        "lines_of_code": 1000,
        "duration": {"start": "2024-01-01", "end": "2024-12-31", "days": 365},
        "activity_mix": {"code": 10, "test": 0, "doc": 0},
        "skills": [],
        "languages": [],
    }
    
    git_metrics = {
        "authors": [],
        "commits": 50,
        "by_activity": {"code": 50, "test": 0, "doc": 0},
        "duration": {
            "first_commit_iso": "2023-06-01",
            "last_commit_iso": "2024-06-01",
            "days": 366,
        },
    }
    
    local_pi = from_local("/path/to/project", local_metrics)
    git_pi = from_git("/path/to/project", git_metrics)
    merged_pi = merge_local_git(local_pi, git_pi)
    
    # Should take wider span: git start (2023-06-01) to local end (2024-12-31)
    assert merged_pi.duration["start"] == "2023-06-01"
    assert merged_pi.duration["end"] == "2024-12-31"


def test_union_case_insensitive():
    """Test that union of lists is case-insensitive but preserves first occurrence."""
    local_metrics = {
        "lines_of_code": 1000,
        "skills": ["Python", "docker"],
        "languages": ["Python"],
        "activity_mix": {"code": 10, "test": 0, "doc": 0},
    }
    
    git_metrics = {
        "authors": [],
        "commits": 10,
        "by_activity": {"code": 10, "test": 0, "doc": 0},
        "languages": [{"ext": ".py", "count": 10}],  # Will become "Python"
    }
    
    local_pi = from_local("/path/to/project", local_metrics)
    git_pi = from_git("/path/to/project", git_metrics)
    
    # Add Docker skill with different case manually to git_pi for testing
    git_pi.skills = ["Docker"]  # Different case from "docker" in local
    
    merged_pi = merge_local_git(local_pi, git_pi)
    
    # Should have Python and docker/Docker (but not both "docker" and "Docker")
    # Count how many docker variants we have
    docker_variants = [s for s in merged_pi.skills if s.lower() == "docker"]
    assert len(docker_variants) == 1, "Should only have one docker variant"
    
    # Should have Python too
    python_variants = [s for s in merged_pi.skills if s.lower() == "python"]
    assert len(python_variants) == 1, "Should only have one Python variant"


def test_missing_fields_robustness():
    """Test that missing fields don't crash the aggregator."""
    # Minimal metrics
    local_metrics = {}
    git_metrics = {}
    
    # Should not crash
    local_pi = from_local("/path/to/project", local_metrics)
    git_pi = from_git("/path/to/repo", git_metrics)
    
    # Should have defaults
    assert local_pi.lines_of_code == 0
    assert local_pi.skills == []
    assert git_pi.authors == []
    assert git_pi.totals["commits"] == 0
    
    # Merge should also work
    merged_pi = merge_local_git(local_pi, git_pi)
    assert merged_pi.source == "merged"

