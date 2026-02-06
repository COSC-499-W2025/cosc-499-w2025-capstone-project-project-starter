import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.services.snapshot_service import SnapshotService


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_repo_with_commits(repo: Path, count: int = 5) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.name", "Snapshot Tester")
    _git(repo, "config", "user.email", "snapshot@test.local")

    for i in range(count):
        file_path = repo / "main.py"
        file_path.write_text(f"print('commit {i}')\n", encoding="utf-8")
        _git(repo, "add", "main.py")
        _git(repo, "commit", "-m", f"commit-{i}")


def test_create_midpoint_snapshot_from_local_git_repo(tmp_path):
    repo = tmp_path / "repo"
    _init_repo_with_commits(repo, count=5)
    commits = _git(repo, "rev-list", "--reverse", "HEAD").splitlines()
    expected_midpoint = commits[2]

    service = SnapshotService(db=None)
    service.project_repo = SimpleNamespace(get=lambda _project_id: SimpleNamespace(root_path=str(repo), source_url=None))
    persisted = []
    service.snapshot_repo = SimpleNamespace(
        create=lambda obj: _capture_snapshot_create(obj, persisted)
    )

    result = service.create_midpoint_snapshot(project_id=123)

    assert result["commit_hash"] == expected_midpoint
    assert result["commit_index"] == 2
    assert result["total_commits"] == 5
    assert result["snapshot_id"] == 1
    assert len(persisted) == 1
    payload = persisted[0]
    assert payload["commit"]["hash"] == expected_midpoint
    assert payload["summary"]["total_files"] >= 1


def test_create_midpoint_snapshot_requires_git_repo(tmp_path):
    no_git_dir = tmp_path / "nogit"
    no_git_dir.mkdir(parents=True, exist_ok=True)
    (no_git_dir / "main.py").write_text("print('no git')\n", encoding="utf-8")

    service = SnapshotService(db=None)
    service.project_repo = SimpleNamespace(
        get=lambda _project_id: SimpleNamespace(root_path=str(no_git_dir), source_url=None)
    )

    with pytest.raises(HTTPException) as exc:
        service.create_midpoint_snapshot(project_id=1)

    assert exc.value.status_code == 400


def _capture_snapshot_create(obj, persisted: list):
    import json
    from datetime import datetime, timezone

    payload = json.loads(obj.payload_json)
    persisted.append(payload)
    obj.id = 1
    obj.created_at = datetime.now(timezone.utc)
    return obj
