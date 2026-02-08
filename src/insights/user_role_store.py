"""
user_role_store.py
------------------
SQLite-backed storage for user-editable project roles.
This keeps user edits separate from immutable insight payloads.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, Dict, Optional

from .storage import DEFAULT_DB_PATH, PROJECTS_TABLE, ProjectInsightsStore

ROLE_TABLE = "project_user_metadata"
ROLE_MIGRATIONS_TABLE = "role_schema_migrations"
PROJECT_TABLE = PROJECTS_TABLE


def _utcnow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


class ProjectRoleStore:
    """Storage API for project user roles kept separate from insights blobs."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.RLock()
        self._apply_migrations()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _apply_migrations(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {ROLE_MIGRATIONS_TABLE} (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    );
                    """
                )
                row = conn.execute(
                    f"SELECT MAX(version) FROM {ROLE_MIGRATIONS_TABLE};"
                ).fetchone()
                current_version = row[0] or 0
                if current_version < 1:
                    self._apply_role_schema(conn)
                    conn.execute(
                        f"INSERT INTO {ROLE_MIGRATIONS_TABLE} (version, applied_at) VALUES (?, ?);",
                        (1, _utcnow()),
                    )
                conn.commit()

    def _apply_role_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ROLE_TABLE} (
                project_id INTEGER PRIMARY KEY,
                user_role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES {PROJECT_TABLE}(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{ROLE_TABLE}_updated ON {ROLE_TABLE}(updated_at);"
        )

    def _resolve_project_id(self, conn: sqlite3.Connection, zip_hash: str, project_name: str) -> Optional[int]:
        row = conn.execute(
            f"""
            SELECT p.id
            FROM {PROJECT_TABLE} p
            WHERE p.source_hash = ? AND p.project_name = ?;
            """,
            (zip_hash, project_name),
        ).fetchone()
        return row[0] if row else None

    def set_user_role(self, zip_hash: str, project_name: str, user_role: Optional[str]) -> bool:
        role = user_role.strip() if isinstance(user_role, str) else None
        with self._lock:
            with self._connect() as conn:
                project_id = self._resolve_project_id(conn, zip_hash, project_name)
                if project_id is None:
                    return False
                if not role:
                    conn.execute(
                        f"DELETE FROM {ROLE_TABLE} WHERE project_id = ?;",
                        (project_id,),
                    )
                    conn.commit()
                    return True
                now = _utcnow()
                conn.execute(
                    f"""
                    INSERT INTO {ROLE_TABLE} (project_id, user_role, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        user_role = excluded.user_role,
                        updated_at = excluded.updated_at;
                    """,
                    (project_id, role, now, now),
                )
                conn.commit()
                return True

    def get_user_role(self, zip_hash: str, project_name: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT m.user_role
                FROM {ROLE_TABLE} m
                JOIN {PROJECT_TABLE} p ON m.project_id = p.id
                WHERE p.source_hash = ? AND p.project_name = ?;
                """,
                (zip_hash, project_name),
            ).fetchone()
            return row[0] if row else None

    def merge_role_into_payload(
        self,
        payload: Dict[str, Any],
        zip_hash: str,
        project_name: str,
    ) -> Dict[str, Any]:
        role = self.get_user_role(zip_hash, project_name)
        if role:
            merged = dict(payload)
            merged["user_role"] = role
            return merged
        return payload


def load_project_insight_with_role(
    zip_hash: str,
    project_name: str,
    db_path: Optional[str] = None,
    store: Optional[ProjectInsightsStore] = None,
    role_store: Optional[ProjectRoleStore] = None,
) -> Optional[Dict[str, Any]]:
    """Load a project insight and merge user_role without mutating stored blobs."""
    insights_store = store or ProjectInsightsStore(db_path=db_path)
    role_store = role_store or ProjectRoleStore(db_path=db_path)
    payload = insights_store.load_project_insight(zip_hash, project_name)
    if payload is None:
        return None
    return role_store.merge_role_into_payload(payload, zip_hash, project_name)


def resolve_db_path(db_url: Optional[str] = None) -> str:
    env_url = os.getenv("DATABASE_URL")
    effective = db_url or env_url or f"sqlite:///{DEFAULT_DB_PATH}"
    return effective.replace("sqlite:///", "")
