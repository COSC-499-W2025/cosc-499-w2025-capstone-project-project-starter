"""Shared helpers for insights tests."""

from typing import Dict, Tuple


def build_pipeline_payload(
    project_names: Tuple[str, ...] = ("ProjectAlpha", "ProjectBeta"),
    include_presentation: bool = True,
) -> Dict[str, Dict]:
    """
    Build a synthetic pipeline payload used across insights tests.
    When include_presentation is True, also attaches project_metrics, portfolio_item,
    and resume_item to mirror what the orchestrator stores.
    """
    projects = {}
    for idx, name in enumerate(project_names):
        projects[name] = {
            "project_name": name,
            "project_path": f"/tmp/{name.lower()}",
            "is_git_repo": idx == 0,
            "git_analysis": {"total_commits": (idx + 1) * 5},
            "categorized_contents": {
                "code": [f"{name.lower()}/code.py"],
                "code_by_language": {"python": [f"{name.lower()}/code.py"]},
                "documentation": [f"{name.lower()}/README.md"],
                "images": [],
                "other": ["video/demo.mp4"],
            },
            "analysis_results": {
                "documentation": {"totals": {"total_words": 120 + idx, "total_files": 1}},
                "code": {"metrics": {"total_files": 1, "total_lines": 42 + idx, "languages": ["python"]}},
                "images": [],
                "videos": {
                    "metrics": {"total_videos": 0, "total_duration": 0},
                    "files": [],
                },
            },
        }

        if include_presentation:
            from src.project.presentation import (
                extract_project_metrics,
                generate_portfolio_item,
                generate_resume_item,
            )

            metrics = extract_project_metrics(projects[name])
            projects[name]["project_metrics"] = metrics.to_dict()
            projects[name]["portfolio_item"] = generate_portfolio_item(projects[name], metrics=metrics)
            projects[name]["resume_item"] = generate_resume_item(projects[name], metrics=metrics)

    payload = {
        "zip_metadata": {
            "root_name": "demo-root",
            "file_count": 20,
            "total_uncompressed_bytes": 12345,
            "total_compressed_bytes": 6789,
        },
        "projects": projects,
    }
    return payload
