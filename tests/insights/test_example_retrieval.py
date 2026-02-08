import sys

from src.insights import example_retrieval
from src.insights.storage import ProjectInsightsStore
from tests.insights.utils import build_pipeline_payload


def _add_misc_payload(payload):
    payload["projects"]["_misc_files"] = {
        "project_name": "_misc_files",
        "project_path": "/tmp/misc",
        "is_git_repo": False,
        "git_analysis": {},
        "categorized_contents": {
            "code": ["misc/script.sh"],
            "code_by_language": {"shell": ["misc/script.sh"]},
            "documentation": ["misc/notes.txt"],
            "images": [],
            "other": ["misc/video.mp4"],
        },
        "analysis_results": {
            "documentation": {"totals": {"total_files": 1, "total_words": 2}},
            "code": {"metrics": {"total_files": 1, "total_lines": 1, "languages": ["shell"]}, "files": []},
            "images": [],
            "videos": {"metrics": {"total_videos": 1, "total_duration": 10}, "files": []},
        },
    }
    return payload


def test_example_retrieval_emits_full_summary(tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "insights.db"
    store = ProjectInsightsStore(db_path=str(db_path))
    payload = _add_misc_payload(build_pipeline_payload())
    store.record_pipeline_run("tests/categorize/demo_projects.zip", payload)
    zip_hash = store.list_recent_zipfiles(limit=1)[0]["zip_hash"]

    args = ["example_retrieval", "--db-path", str(db_path), "--zip-hash", zip_hash]
    monkeypatch.setattr(sys, "argv", args)

    example_retrieval.main()

    output = capsys.readouterr().out
    assert "Retrieval From Database" in output
    assert "Project: ProjectAlpha" in output
    assert "Project: ProjectBeta" in output
    assert "Miscellaneous Files (not in any project)" in output
    assert "Retrieval Complete - All results printed above" in output
