from __future__ import annotations

import hashlib
import os
import posixpath
import tempfile
import zipfile
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.db.consents import latest_consent_granted
from git import Repo, InvalidGitRepositoryError


@dataclass(frozen=True)
class IngestResult:
    user_id: str
    portfolio_id: str
    created_projects: List[Dict]
    skipped_projects: List[Dict]


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_zip_relpath(name: str) -> Optional[str]:
    name = name.replace("\\", "/")
    name = posixpath.normpath(name)

    if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/":
        return None
    if name == "." or name == "..":
        return None
    return name


def _blob_path(blobstore_root: str, sha256: str) -> str:
    subdir = sha256[:2]
    return os.path.join(blobstore_root, subdir, sha256)


def _ensure_user_and_portfolio(conn, user_id: Optional[str], portfolio_id: Optional[str]) -> Tuple[str, str]:
    if user_id is None:
        user_id = str(conn.execute(text("INSERT INTO users DEFAULT VALUES RETURNING id")).scalar_one())

    conn.execute(
        text(
            """
            INSERT INTO user_config (user_id, config_json)
            VALUES (:user_id, '{}'::jsonb)
            ON CONFLICT (user_id) DO NOTHING
            """
        ),
        {"user_id": user_id},
    )

    if portfolio_id is None:
        row = conn.execute(
            text("SELECT id FROM portfolios WHERE user_id = :user_id AND name = 'default' ORDER BY created_at ASC LIMIT 1"),
            {"user_id": user_id},
        ).scalar()
        if row:
            portfolio_id = str(row)
        else:
            portfolio_id = str(
                conn.execute(
                    text("INSERT INTO portfolios (user_id, name) VALUES (:user_id, 'default') RETURNING id"),
                    {"user_id": user_id},
                ).scalar_one()
            )

    return user_id, portfolio_id


def _require_data_access_consent(conn, user_id: str) -> None:
    granted = conn.execute(
        text(
            """
            SELECT granted
            FROM privacy_consents
            WHERE user_id = :user_id AND consent_type = 'data_access'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).scalar()
    if granted is not True:
        raise PermissionError("data_access consent not granted")


def save_upload_to_temp(upload_bytes: bytes) -> str:
    fd, path = tempfile.mkstemp(prefix="artifactminer-", suffix=".zip")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(upload_bytes)
    return path


# -----------------------------
# Function to extract commits
# -----------------------------
def extract_commits_from_git_zip(zip_path: str):
    tmpdir = tempfile.mkdtemp()
    try:
        # Unzip repo
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)

        # Open Git repo with repo.head to dynamically fetch the branch name
        # and avoid relying on OS level factors
        repo = Repo(tmpdir)
        commits = list(repo.iter_commits(repo.head))
        return [c.message.strip() for c in commits]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def find_git_repo(path: str) -> Repo:
    """
    Recursively search for a .git folder starting at path.
    Returns a Repo object if found, else raises InvalidGitRepositoryError.
    """
    for root, dirs, files in os.walk(path):
        if '.git' in dirs:
            try:
                return Repo(root)
            except InvalidGitRepositoryError:
                continue
    raise InvalidGitRepositoryError(f"No git repo found in {path}")


def ingest_zip_to_db(
    *,
    engine: Engine,
    zip_path: str,
    zip_filename: str,
    blobstore_root: str,
    user_id: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    project_name: Optional[str] = None,
    snapshot_label: Optional[str] = None,
) -> IngestResult:
    zip_sha = _sha256_file(zip_path)

    os.makedirs(blobstore_root, exist_ok=True)

    created_projects: List[Dict] = []
    skipped_projects: List[Dict] = []

    with engine.begin() as conn:
        user_id2, portfolio_id2 = _ensure_user_and_portfolio(conn, user_id, portfolio_id)
        _require_data_access_consent(conn, user_id2)

        external_allowed_at_ingest = latest_consent_granted(conn, user_id2, "external_services") is True

        with zipfile.ZipFile(zip_path, "r") as zf:
            entries: List[Tuple[str, zipfile.ZipInfo]] = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if "__MACOSX" in info.filename:
                    continue
                safe = _safe_zip_relpath(info.filename)
                if safe is None:
                    continue
                entries.append((safe, info))

            project_to_files: Dict[str, List[Tuple[str, zipfile.ZipInfo]]] = {}
            if project_name:
                project_to_files[project_name] = entries
            else:
                for rel, info in entries:
                    parts = rel.split("/")
                    top = parts[0] if len(parts) > 1 else "__root__"
                    project_to_files.setdefault(top, []).append((rel, info))

            for proj_key, files in project_to_files.items():
                proj_display = proj_key if proj_key != "__root__" else (project_name or zip_filename)

                proj_id = conn.execute(
                    text(
                        """
                        SELECT id FROM projects
                        WHERE portfolio_id = :portfolio_id AND name = :name
                        ORDER BY created_at ASC LIMIT 1
                        """
                    ),
                    {"portfolio_id": portfolio_id2, "name": proj_display},
                ).scalar()

                if not proj_id:
                    # Let DB default apply, and allow git_metrics to make it authoritative later.
                    proj_id = conn.execute(
                        text(
                            """
                            INSERT INTO projects (portfolio_id, name, project_type, evidence_json)
                            VALUES (:portfolio_id, :name, 'code', '{}'::jsonb)
                            RETURNING id
                            """
                        ),
                        {"portfolio_id": portfolio_id2, "name": proj_display},
                    ).scalar_one()

                proj_id = str(proj_id)

                snap_id = conn.execute(
                    text(
                        """
                        SELECT id FROM snapshots
                        WHERE project_id = :project_id AND source_zip_sha256 = :zip_sha
                        LIMIT 1
                        """
                    ),
                    {"project_id": proj_id, "zip_sha": zip_sha},
                ).scalar()

                if snap_id:
                    skipped_projects.append(
                        {"project_id": proj_id, "project_name": proj_display, "snapshot_id": str(snap_id), "zip_sha256": zip_sha}
                    )
                    continue

                snap_id = conn.execute(
                    text(
                        """
                        INSERT INTO snapshots (project_id, source_zip_name, source_zip_sha256, snapshot_label)
                        VALUES (:project_id, :zip_name, :zip_sha, :label)
                        RETURNING id
                        """
                    ),
                    {"project_id": proj_id, "zip_name": zip_filename, "zip_sha": zip_sha, "label": snapshot_label},
                ).scalar_one()
                snap_id = str(snap_id)

                # Always queue local analyses; queue external only if consent already granted.
                if external_allowed_at_ingest:
                    conn.execute(
                        text(
                            """
                            INSERT INTO analyses (snapshot_id, analysis_type, status)
                            VALUES
                              (:sid, 'parser', 'pending'),
                              (:sid, 'local_ml', 'pending'),
                              (:sid, 'git_metrics', 'pending'),
                              (:sid, 'external_llm', 'pending')
                            """
                        ),
                        {"sid": snap_id},
                    )
                else:
                    conn.execute(
                        text(
                            """
                            INSERT INTO analyses (snapshot_id, analysis_type, status)
                            VALUES
                              (:sid, 'parser', 'pending'),
                              (:sid, 'local_ml', 'pending'),
                              (:sid, 'git_metrics', 'pending')
                            """
                        ),
                        {"sid": snap_id},
                    )

                for rel, info in files:
                    if project_name:
                        rel_in_project = rel
                    else:
                        parts = rel.split("/", 1)
                        rel_in_project = parts[1] if len(parts) == 2 else parts[0]

                    with zf.open(info, "r") as fp:
                        data = fp.read()

                    sha = hashlib.sha256(data).hexdigest()
                    stored_path = _blob_path(blobstore_root, sha)
                    os.makedirs(os.path.dirname(stored_path), exist_ok=True)

                    if not os.path.exists(stored_path):
                        tmp_path = stored_path + ".tmp"
                        with open(tmp_path, "wb") as out:
                            out.write(data)
                        os.replace(tmp_path, stored_path)

                    conn.execute(
                        text(
                            """
                            INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                            VALUES (:sha, :sz, NULL, :path)
                            ON CONFLICT (sha256) DO NOTHING
                            """
                        ),
                        {"sha": sha, "sz": int(len(data)), "path": stored_path},
                    )

                    dt = None
                    try:
                        dt = getattr(info, "date_time", None)
                        if dt:
                            # stored as naive; DB column is timestamptz, Postgres will interpret per server tz.
                            # acceptable for milestone scope.
                            dt = datetime(*dt)  # type: ignore[name-defined]
                    except Exception:
                        dt = None

                    conn.execute(
                        text(
                            """
                            INSERT INTO snapshot_files
                              (snapshot_id, relative_path, file_sha256, last_modified_ts, file_mode, size_bytes)
                            VALUES
                              (:sid, :rel, :sha, :ts, :mode, :sz)
                            """
                        ),
                        {
                            "sid": snap_id,
                            "rel": rel_in_project,
                            "sha": sha,
                            "ts": None,
                            "mode": None,
                            "sz": int(len(data)),
                        },
                    )

                created_projects.append(
                    {"project_id": proj_id, "project_name": proj_display, "snapshot_id": snap_id, "zip_sha256": zip_sha}
                )

    return IngestResult(
        user_id=str(user_id2),
        portfolio_id=str(portfolio_id2),
        created_projects=created_projects,
        skipped_projects=skipped_projects,
    )
