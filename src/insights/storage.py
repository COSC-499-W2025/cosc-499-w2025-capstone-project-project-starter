"""
storage.py
----------
SQLite-backed persistence layer for storing grouped pipeline insights.
The legacy encrypted blob tables remain for backward compatibility, but the
active codepaths read/write grouped rows.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import zlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DB_URL = "sqlite:///data/app.db"
DEFAULT_DB_PATH = DEFAULT_DB_URL.replace("sqlite:///", "")
# Fixed local encryption key (overridable via INSIGHTS_ENCRYPTION_KEY env var)
DEFAULT_INSIGHTS_KEY = os.getenv("INSIGHTS_ENCRYPTION_KEY", "local-insights-key")
SCHEMA_VERSION = 6

# Legacy tables (no longer written)
LEGACY_ZIP_TABLE = "zipfile"

# Grouped tables
DELETION_AUDIT_TABLE = "deletion_audit"
INGEST_TABLE = "ingest"
PROJECTS_TABLE = "projects"
PROJECT_INFO_TABLE = "project_info"
FILES_TABLE = "files"
FILE_INFO_TABLE = "file_info"
FILE_ANALYSIS_CACHE_TABLE = "file_analysis_cache"
PORTFOLIO_INSIGHTS_TABLE = "portfolio_insights"
RESUME_BULLETS_TABLE = "resume_bullets"
TAGS_TABLE = "tags"
SKILL_EVIDENCE_TABLE = "skill_evidence"
RANKING_TABLE = "ranking"
CHRONOLOGY_TABLE = "chronology"
THUMBNAILS_TABLE = "thumbnails"
PRESENTATION_TABLE = "presentation"
PROFILE_TABLE = "profile"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _canonical_dumps(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _iso_to_datetime(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


class SecureSerializer:
    """Compresses and encrypts insights before storing them in SQLite."""

    def __init__(self, key: Optional[bytes]) -> None:
        if key is None:
            env_key = DEFAULT_INSIGHTS_KEY
            key = env_key.encode("utf-8") if isinstance(env_key, str) else env_key
        if isinstance(key, str):  # pragma: no cover - defensive
            key = key.encode("utf-8")
        self._root_key = hashlib.sha256(key).digest()

    def _derive_stream(self, iv: bytes, length: int) -> bytes:
        """Derive a pseudo-random keystream using HMAC-SHA256."""
        stream = bytearray()
        counter = 0
        while len(stream) < length:
            counter_bytes = counter.to_bytes(4, "big")
            block = hmac.new(self._root_key, iv + counter_bytes, hashlib.sha256).digest()
            stream.extend(block)
            counter += 1
        return bytes(stream[:length])

    def encrypt(self, payload: Dict[str, Any]) -> bytes:
        serialized = _canonical_dumps(payload).encode("utf-8")
        compressed = zlib.compress(serialized, level=9)
        iv = os.urandom(16)
        keystream = self._derive_stream(iv, len(compressed))
        ciphertext = bytes(a ^ b for a, b in zip(compressed, keystream))
        mac = hmac.new(self._root_key, iv + ciphertext, hashlib.sha256).digest()
        return iv + ciphertext + mac

    def decrypt(self, blob: bytes) -> Dict[str, Any]:
        if len(blob) <= 48:
            raise ValueError("Ciphertext is too short to decrypt.")
        iv = blob[:16]
        mac = blob[-32:]
        ciphertext = blob[16:-32]
        expected_mac = hmac.new(self._root_key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("Ciphertext failed integrity verification.")
        keystream = self._derive_stream(iv, len(ciphertext))
        compressed = bytes(a ^ b for a, b in zip(ciphertext, keystream))
        decompressed = zlib.decompress(compressed)
        return json.loads(decompressed.decode("utf-8"))


class PayloadValidationError(ValueError):
    """Raised when the pipeline output does not meet schema requirements."""


@dataclass(frozen=True)
class InsightStats:
    inserted: int
    updated: int
    unchanged: int
    deleted: int
    project_count: int
    metadata_updated: bool


class ProjectInsightsStore:
    """High-level API for persisting project insights in SQLite."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        encryption_key: Optional[bytes] = None,
    ) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        _ensure_parent(self.db_path)
        self.serializer = SecureSerializer(encryption_key)
        self._lock = threading.RLock()
        self._apply_migrations()

 
    # DB bootstrap & migrations
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _apply_migrations(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    );
                    """
                )
                row = conn.execute(
                    "SELECT MAX(version) FROM schema_migrations;"
                ).fetchone()
                current_version = row[0] or 0
                if current_version < 1:
                    self._apply_initial_schema(conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                        (1, _utcnow()),
                    )
                    current_version = 1
                if current_version < 2:
                    self._apply_audit_schema(conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                        (2, _utcnow()),
                    )
                    current_version = 2
                if current_version < 5:
                    self._apply_grouped_schema(conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                        (5, _utcnow()),
                    )
                    current_version = 5
                if current_version < 6:
                    self._apply_project_info_name_migration(conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                        (6, _utcnow()),
                    )
                conn.commit()

    def _apply_initial_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {LEGACY_ZIP_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zip_hash TEXT UNIQUE NOT NULL,
                zip_path TEXT NOT NULL,
                metadata_hash TEXT NOT NULL,
                metadata_encrypted BLOB NOT NULL,
                total_projects INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_pipeline_version TEXT,
                backup_marker TEXT
            );
            """
        )

    def _apply_audit_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DELETION_AUDIT_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                scope TEXT NOT NULL,
                details TEXT,
                deleted_projects INTEGER NOT NULL DEFAULT 0,
                deleted_zips INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )

    def _apply_grouped_schema(self, conn: sqlite3.Connection) -> None:
        """Ensure grouped tables exist for report-ready storage."""
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INGEST_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL CHECK (source_type IN ('zip', 'dir')),
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                file_count INTEGER NOT NULL DEFAULT 0,
                total_uncompressed_bytes INTEGER NOT NULL DEFAULT 0,
                total_compressed_bytes INTEGER NOT NULL DEFAULT 0,
                run_type TEXT NOT NULL CHECK (run_type IN ('full', 'incremental')),
                parent_run_id INTEGER,
                pipeline_version TEXT,
                status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('running', 'completed', 'failed')),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(parent_run_id) REFERENCES {INGEST_TABLE}(id) ON DELETE SET NULL
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{INGEST_TABLE}_source_hash ON {INGEST_TABLE}(source_hash);"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{INGEST_TABLE}_source_run ON {INGEST_TABLE}(source_hash, id);"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PROJECTS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT NOT NULL,
                project_key TEXT NOT NULL,
                project_name TEXT NOT NULL,
                slug TEXT NOT NULL,
                root_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source_hash, project_key)
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{PROJECTS_TABLE}_source ON {PROJECTS_TABLE}(source_hash);"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PROJECT_INFO_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                ingest_id INTEGER NOT NULL,
                project_name TEXT,
                project_path TEXT,
                is_git_repo INTEGER NOT NULL DEFAULT 0,
                total_files INTEGER NOT NULL DEFAULT 0,
                total_lines INTEGER NOT NULL DEFAULT 0,
                total_commits INTEGER NOT NULL DEFAULT 0,
                total_contributors INTEGER NOT NULL DEFAULT 0,
                activity_code INTEGER NOT NULL DEFAULT 0,
                activity_test INTEGER NOT NULL DEFAULT 0,
                activity_doc INTEGER NOT NULL DEFAULT 0,
                duration_start TEXT,
                duration_end TEXT,
                duration_days INTEGER NOT NULL DEFAULT 0,
                doc_files INTEGER NOT NULL DEFAULT 0,
                doc_words INTEGER NOT NULL DEFAULT 0,
                image_files INTEGER NOT NULL DEFAULT 0,
                video_files INTEGER NOT NULL DEFAULT 0,
                test_files INTEGER NOT NULL DEFAULT 0,
                has_documentation INTEGER NOT NULL DEFAULT 0 CHECK (has_documentation IN (0, 1)),
                has_tests INTEGER NOT NULL DEFAULT 0 CHECK (has_tests IN (0, 1)),
                has_images INTEGER NOT NULL DEFAULT 0 CHECK (has_images IN (0, 1)),
                has_videos INTEGER NOT NULL DEFAULT 0 CHECK (has_videos IN (0, 1)),
                languages_json TEXT,
                frameworks_json TEXT,
                skills_json TEXT,
                keyword_tags_json TEXT,
                contributors_json TEXT,
                tags_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES {PROJECTS_TABLE}(id) ON DELETE CASCADE,
                FOREIGN KEY(ingest_id) REFERENCES {INGEST_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(project_id, ingest_id)
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{PROJECT_INFO_TABLE}_ingest ON {PROJECT_INFO_TABLE}(ingest_id);"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FILES_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                relative_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                extension TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(project_id, relative_path),
                FOREIGN KEY(project_id) REFERENCES {PROJECTS_TABLE}(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FILE_INFO_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                project_info_id INTEGER NOT NULL,
                content_hash TEXT,
                content_size_bytes INTEGER NOT NULL DEFAULT 0,
                content_mime_type TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                modified_at TEXT,
                is_binary INTEGER NOT NULL DEFAULT 0 CHECK (is_binary IN (0, 1)),
                is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
                language TEXT,
                category TEXT CHECK (category IN ('code', 'documentation', 'images', 'video', 'other')),
                metrics_json TEXT,
                tags_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(file_id) REFERENCES {FILES_TABLE}(id) ON DELETE CASCADE,
                FOREIGN KEY(project_info_id) REFERENCES {PROJECT_INFO_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(file_id, project_info_id)
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{FILE_INFO_TABLE}_project ON {FILE_INFO_TABLE}(project_info_id);"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{FILE_INFO_TABLE}_content ON {FILE_INFO_TABLE}(content_hash);"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FILE_ANALYSIS_CACHE_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256 TEXT NOT NULL,
                file_ext TEXT,
                analysis_type TEXT NOT NULL CHECK (analysis_type IN ('code', 'text', 'video', 'image')),
                analysis_result BLOB NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(sha256, analysis_type)
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{FILE_ANALYSIS_CACHE_TABLE}_sha256 ON {FILE_ANALYSIS_CACHE_TABLE}(sha256);"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{FILE_ANALYSIS_CACHE_TABLE}_type ON {FILE_ANALYSIS_CACHE_TABLE}(sha256, analysis_type);"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PORTFOLIO_INSIGHTS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_info_id INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                pipeline_version TEXT,
                tagline TEXT,
                description TEXT,
                project_type TEXT,
                complexity TEXT,
                is_collaborative INTEGER NOT NULL DEFAULT 0 CHECK (is_collaborative IN (0, 1)),
                summary TEXT,
                key_features_json TEXT,
                FOREIGN KEY(project_info_id) REFERENCES {PROJECT_INFO_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(project_info_id)
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RESUME_BULLETS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_insight_id INTEGER NOT NULL,
                bullet_text TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                is_selected INTEGER NOT NULL DEFAULT 1 CHECK (is_selected IN (0, 1)),
                source TEXT NOT NULL DEFAULT 'generated' CHECK (source IN ('generated', 'manual')),
                FOREIGN KEY(portfolio_insight_id) REFERENCES {PORTFOLIO_INSIGHTS_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(portfolio_insight_id, display_order)
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TAGS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_type TEXT NOT NULL CHECK (tag_type IN ('language', 'framework', 'skill', 'design_pattern', 'keyword', 'tool')),
                name TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(tag_type, name)
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SKILL_EVIDENCE_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_info_id INTEGER NOT NULL,
                file_info_id INTEGER,
                tag_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL,
                location TEXT,
                reasoning TEXT,
                confidence REAL,
                FOREIGN KEY(project_info_id) REFERENCES {PROJECT_INFO_TABLE}(id) ON DELETE CASCADE,
                FOREIGN KEY(file_info_id) REFERENCES {FILE_INFO_TABLE}(id) ON DELETE SET NULL,
                FOREIGN KEY(tag_id) REFERENCES {TAGS_TABLE}(id) ON DELETE RESTRICT
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RANKING_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingest_id INTEGER NOT NULL,
                criteria TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ranking_json TEXT NOT NULL,
                FOREIGN KEY(ingest_id) REFERENCES {INGEST_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(ingest_id)
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CHRONOLOGY_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingest_id INTEGER NOT NULL,
                chronology_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(ingest_id) REFERENCES {INGEST_TABLE}(id) ON DELETE CASCADE,
                UNIQUE(ingest_id)
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {THUMBNAILS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_info_id INTEGER,
                file_info_id INTEGER,
                role TEXT NOT NULL CHECK (role IN ('project', 'portfolio', 'resume', 'file')),
                image_path TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                mime_type TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_info_id) REFERENCES {PROJECT_INFO_TABLE}(id) ON DELETE CASCADE,
                FOREIGN KEY(file_info_id) REFERENCES {FILE_INFO_TABLE}(id) ON DELETE SET NULL
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PRESENTATION_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                profile_type TEXT NOT NULL CHECK (profile_type IN ('portfolio', 'resume')),
                profile_name TEXT NOT NULL,
                controls_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user_configurations(user_id) ON DELETE SET NULL
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PROFILE_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                presentation_id INTEGER NOT NULL,
                selections_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(presentation_id) REFERENCES {PRESENTATION_TABLE}(id) ON DELETE CASCADE
            );
            """
        )

    # File Analysis Cache API
    def cache_file_analysis(
        self,
        sha256: str,
        analysis_type: str,
        analysis_result: Dict[str, Any],
        file_ext: Optional[str] = None,
    ) -> None:
        """
        Store or update file analysis results in cache.
        
        Args:
            sha256: SHA256 hash of the file content
            analysis_type: Type of analysis ('code', 'text', 'video', 'image')
            analysis_result: Dictionary containing analysis results
            file_ext: File extension (optional)
        """
        if analysis_type not in ('code', 'text', 'video', 'image'):
            raise ValueError(f"Invalid analysis_type: {analysis_type}")
        
        encrypted_result = self.serializer.encrypt(analysis_result)
        now = _utcnow()
        
        with self._lock:
            with self._connect() as conn:
                # Try to insert, or update if exists
                conn.execute(
                    f"""
                    INSERT INTO {FILE_ANALYSIS_CACHE_TABLE}
                        (sha256, file_ext, analysis_type, analysis_result, created_at, last_accessed, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(sha256, analysis_type) DO UPDATE SET
                        analysis_result = excluded.analysis_result,
                        last_accessed = excluded.last_accessed,
                        file_ext = excluded.file_ext;
                    """,
                    (sha256, file_ext, analysis_type, encrypted_result, now, now),
                )
                conn.commit()
    
    def get_cached_file_analysis(
        self,
        sha256: str,
        analysis_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached file analysis results.
        
        Args:
            sha256: SHA256 hash of the file content
            analysis_type: Type of analysis to retrieve
            
        Returns:
            Dictionary with analysis results, or None if not found
        """
        if analysis_type not in ('code', 'text', 'video', 'image'):
            raise ValueError(f"Invalid analysis_type: {analysis_type}")
        
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    f"""
                    SELECT analysis_result FROM {FILE_ANALYSIS_CACHE_TABLE}
                    WHERE sha256 = ? AND analysis_type = ?;
                    """,
                    (sha256, analysis_type),
                ).fetchone()
                
                if row is None:
                    return None
                
                # Update access tracking
                now = _utcnow()
                conn.execute(
                    f"""
                    UPDATE {FILE_ANALYSIS_CACHE_TABLE}
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE sha256 = ? AND analysis_type = ?;
                    """,
                    (now, sha256, analysis_type),
                )
                conn.commit()
                
                # Decrypt and return result
                encrypted_result = row[0]
                return self.serializer.decrypt(encrypted_result)
    def _apply_project_info_name_migration(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({PROJECT_INFO_TABLE});")}
        if "project_name" in columns:
            return
        conn.execute(f"ALTER TABLE {PROJECT_INFO_TABLE} ADD COLUMN project_name TEXT;")
        conn.execute(
            f"""
            UPDATE {PROJECT_INFO_TABLE}
            SET project_name = (
                SELECT project_name FROM {PROJECTS_TABLE} p
                WHERE p.id = {PROJECT_INFO_TABLE}.project_id
            )
            WHERE project_name IS NULL;
            """
        )

    # Public API
    def record_pipeline_run(
        self,
        zip_path: str,
        pipeline_result: Dict[str, Any],
        pipeline_version: str = "1.0",
    ) -> InsightStats:
        payload = self._validate_pipeline_result(pipeline_result)
        metadata = payload["zip_metadata"]
        projects = payload["projects"]
        extras = payload.get("extras", {})
        file_info_lookup = self._build_file_info_lookup(extras)

        source_hash = self._derive_zip_hash(zip_path, metadata)
        now = _utcnow()

        stats = {"inserted": 0, "updated": 0, "unchanged": 0, "deleted": 0}
        with self._lock:
            with self._connect() as conn:
                conn.isolation_level = None  # manual transaction
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    ingest_id, metadata_updated = self._insert_ingest_run(
                        conn,
                        source_hash,
                        zip_path,
                        metadata,
                        pipeline_version,
                        now,
                    )
                    for project_name, project_payload in projects.items():
                        project_id = self._upsert_project(
                            conn,
                            source_hash,
                            project_name,
                            project_payload,
                            now,
                        )
                        project_info_id = self._insert_project_info(
                            conn,
                            project_id,
                            ingest_id,
                            project_name,
                            project_payload,
                            now,
                        )
                        self._store_project_files_and_analysis(
                            conn,
                            project_info_id,
                            project_id,
                            project_payload,
                            now,
                            file_info_lookup=file_info_lookup,
                        )
                        self._store_project_metrics(conn, project_info_id, project_payload, now)
                        self._store_project_contributors(conn, project_info_id, project_payload, now)
                        self._store_project_tags(conn, project_info_id, project_payload, now)
                        self._store_portfolio_insights(
                            conn,
                            project_info_id,
                            project_payload,
                            pipeline_version,
                            now,
                        )
                        stats["inserted"] += 1
                    if extras:
                        self._store_global_insights(conn, ingest_id, extras, now)
                    conn.execute("COMMIT;")
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

        return InsightStats(
            inserted=stats["inserted"],
            updated=stats["updated"],
            unchanged=stats["unchanged"],
            deleted=stats["deleted"],
            project_count=len(projects),
            metadata_updated=metadata_updated,
        )

    # Customization API
    def update_portfolio_insights_fields(
        self,
        project_info_id: int,
        fields: Dict[str, Any],
    ) -> bool:
        """
        Update editable fields for a portfolio insight row identified by project_info_id.

        Editable keys: tagline, description, project_type, complexity, is_collaborative,
        summary, key_features (list -> stored as JSON).

        Returns True if a row was updated.
        """
        editable = {
            "tagline",
            "description",
            "project_type",
            "complexity",
            "is_collaborative",
            "summary",
            "key_features",
        }
        update_data: Dict[str, Any] = {}
        for k, v in (fields or {}).items():
            if k in editable:
                update_data[k] = v
        if not update_data:
            return False

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    f"SELECT id FROM {PORTFOLIO_INSIGHTS_TABLE} WHERE project_info_id = ?;",
                    (project_info_id,),
                ).fetchone()
                if not row:
                    return False
                sets = []
                params: List[Any] = []
                if "tagline" in update_data:
                    sets.append("tagline = ?")
                    params.append(update_data["tagline"])
                if "description" in update_data:
                    sets.append("description = ?")
                    params.append(update_data["description"])
                if "project_type" in update_data:
                    sets.append("project_type = ?")
                    params.append(update_data["project_type"])
                if "complexity" in update_data:
                    sets.append("complexity = ?")
                    params.append(update_data["complexity"])
                if "is_collaborative" in update_data:
                    sets.append("is_collaborative = ?")
                    params.append(1 if update_data["is_collaborative"] else 0)
                if "summary" in update_data:
                    sets.append("summary = ?")
                    params.append(update_data["summary"])
                if "key_features" in update_data:
                    sets.append("key_features_json = ?")
                    try:
                        params.append(json.dumps(update_data["key_features"] or []))
                    except Exception:
                        params.append("[]")
                if not sets:
                    return False
                params.append(project_info_id)
                conn.execute(
                    f"UPDATE {PORTFOLIO_INSIGHTS_TABLE} SET " + ", ".join(sets) + " WHERE project_info_id = ?;",
                    tuple(params),
                )
                return True

    def replace_resume_bullets(
        self,
        project_info_id: int,
        bullets: List[str],
    ) -> bool:
        """
        Replace resume bullets for a given project_info_id. All existing bullets are removed
        and replaced with the provided list as manual, selected bullets in display order.

        Returns True if replacement occurred (portfolio insight row existed).
        """
        # Normalize bullets
        cleaned: List[str] = []
        for b in bullets or []:
            if isinstance(b, str):
                s = b.strip()
                if s:
                    cleaned.append(s)

        with self._lock:
            with self._connect() as conn:
                insight_row = conn.execute(
                    f"SELECT id FROM {PORTFOLIO_INSIGHTS_TABLE} WHERE project_info_id = ?;",
                    (project_info_id,),
                ).fetchone()
                if not insight_row:
                    return False
                insight_id = insight_row[0]
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    conn.execute(
                        f"DELETE FROM {RESUME_BULLETS_TABLE} WHERE portfolio_insight_id = ?;",
                        (insight_id,),
                    )
                    for order, text in enumerate(cleaned):
                        conn.execute(
                            f"""
                            INSERT INTO {RESUME_BULLETS_TABLE} (portfolio_insight_id, bullet_text, display_order, is_selected, source)
                            VALUES (?, ?, ?, ?, ?);
                            """,
                            (insight_id, text, order, 1, "manual"),
                        )
                    conn.execute("COMMIT;")
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                return True

    def save_portfolio_customization(
        self,
        project_info_id: int,
        portfolio_fields: Optional[Dict[str, Any]] = None,
        resume_bullets: Optional[List[str]] = None,
    ) -> bool:
        """
        Convenience method to update portfolio fields and/or replace resume bullets.
        Returns True if at least one change was applied.
        """
        changed = False
        if portfolio_fields:
            changed = self.update_portfolio_insights_fields(project_info_id, portfolio_fields) or changed
        if resume_bullets is not None:
            changed = self.replace_resume_bullets(project_info_id, resume_bullets) or changed
        return changed

    def load_project_insight(self, zip_hash: str, project_name: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            ingest_id = self._latest_ingest_id(conn, zip_hash)
            if not ingest_id:
                return None
            project_row = conn.execute(
                f"SELECT id FROM {PROJECTS_TABLE} WHERE source_hash = ? AND project_name = ?;",
                (zip_hash, project_name),
            ).fetchone()
            if not project_row:
                return None
            project_id = project_row[0]
            project_info_id = conn.execute(
                f"""
                SELECT id FROM {PROJECT_INFO_TABLE}
                WHERE project_id = ? AND ingest_id = ?;
                """,
                (project_id, ingest_id),
            ).fetchone()
            if not project_info_id:
                project_info_id = conn.execute(
                    f"""
                    SELECT id FROM {PROJECT_INFO_TABLE}
                    WHERE project_id = ?
                    ORDER BY id DESC LIMIT 1;
                    """,
                    (project_id,),
                ).fetchone()
            if not project_info_id:
                return None
            return self._build_project_payload(conn, project_info_id[0])

    def load_project_insight_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Load project insight payload by project info ID (primary key).

        Args:
            project_id: The project_info.id primary key from the database.

        Returns:
            Normalized project payload dict, or None if project_id not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT id FROM {PROJECT_INFO_TABLE} WHERE id = ?;",
                (project_id,),
            ).fetchone()
            if not row:
                return None
            return self._build_project_payload(conn, project_id)


    def _normalize_resume_bullets(
        self,
        resume_item: Dict[str, Any],
        max_bullets: Optional[int],
    ) -> List[str]:
        if not isinstance(resume_item, dict):
            raise TypeError(f"resume_item must be a dict, got {type(resume_item).__name__}")
        bullets = resume_item.get("bullets")
        if not isinstance(bullets, list):
            raise ValueError("resume_item['bullets'] must be a list")

        cleaned: List[str] = []
        for bullet in bullets:
            if not isinstance(bullet, str):
                raise ValueError("All items in resume_item['bullets'] must be strings")
            stripped = bullet.strip()
            if stripped:
                cleaned.append(stripped)

        if not cleaned:
            raise ValueError("resume_item['bullets'] must contain at least one non-empty bullet after stripping")
        if max_bullets is not None and len(cleaned) > max_bullets:
            raise ValueError(
                f"resume_item['bullets'] cannot exceed {max_bullets} bullets, got {len(cleaned)}"
            )
        return cleaned

    def update_resume_item_by_id(
        self,
        project_info_id: int,
        resume_item: Dict[str, Any],
        *,
        source: str = "manual",
        max_bullets: Optional[int] = 6,
        create_if_missing: bool = True,
    ) -> bool:
        """
        Persist customized resume bullets for a stored project insight.

        Args:
            project_info_id: The project_info.id primary key from the insights database.
            resume_item: Resume item dict containing "bullets" (List[str]) and optional "project_name".
            source: Bullet source label ("manual" or "generated").
            max_bullets: Maximum number of bullets allowed (default 6). Use None to disable.
            create_if_missing: If True, create a portfolio_insights row when missing.

        Returns:
            True if the resume item was updated, False if the project is not found
            or no portfolio insight exists and create_if_missing is False.
        """
        if not isinstance(project_info_id, int):
            raise TypeError(f"project_info_id must be an int, got {type(project_info_id).__name__}")
        if source not in {"generated", "manual"}:
            raise ValueError("source must be 'generated' or 'manual'")

        project_name_value = resume_item.get("project_name")
        if project_name_value is not None:
            if not isinstance(project_name_value, str):
                raise ValueError("resume_item['project_name'] must be a string")
            project_name_value = project_name_value.strip()
            if not project_name_value:
                raise ValueError("resume_item['project_name'] cannot be empty after stripping")

        bullets = self._normalize_resume_bullets(resume_item, max_bullets)

        with self._lock:
            with self._connect() as conn:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    row = conn.execute(
                        f"SELECT id FROM {PROJECT_INFO_TABLE} WHERE id = ?;",
                        (project_info_id,),
                    ).fetchone()
                    if not row:
                        conn.execute("ROLLBACK;")
                        return False

                    if project_name_value is not None:
                        conn.execute(
                            f"""
                            UPDATE {PROJECT_INFO_TABLE}
                            SET project_name = ?, updated_at = ?
                            WHERE id = ?;
                            """,
                            (project_name_value, _utcnow(), project_info_id),
                        )

                    row = conn.execute(
                        f"SELECT id FROM {PORTFOLIO_INSIGHTS_TABLE} WHERE project_info_id = ?;",
                        (project_info_id,),
                    ).fetchone()
                    if not row:
                        if not create_if_missing:
                            conn.execute("ROLLBACK;")
                            return False
                        now = _utcnow()
                        conn.execute(
                            f"""
                            INSERT INTO {PORTFOLIO_INSIGHTS_TABLE} (
                                project_info_id, generated_at, pipeline_version
                            ) VALUES (?, ?, ?);
                            """,
                            (project_info_id, now, "manual"),
                        )
                        portfolio_insight_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]
                    else:
                        portfolio_insight_id = row[0]

                    conn.execute(
                        f"DELETE FROM {RESUME_BULLETS_TABLE} WHERE portfolio_insight_id = ?;",
                        (portfolio_insight_id,),
                    )
                    for order, bullet in enumerate(bullets):
                        conn.execute(
                            f"""
                            INSERT INTO {RESUME_BULLETS_TABLE} (
                                portfolio_insight_id, bullet_text, display_order, is_selected, source
                            ) VALUES (?, ?, ?, ?, ?);
                            """,
                            (portfolio_insight_id, bullet, order, 1, source),
                        )

                    conn.execute("COMMIT;")
                    return True
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

    def load_zip_report(self, zip_hash: str) -> Optional[Dict[str, Any]]:
        """Reconstruct a full zip-level report payload from grouped tables."""
        with self._connect() as conn:
            source_row = conn.execute(
                f"""
                SELECT id, source_name, file_count, total_uncompressed_bytes, total_compressed_bytes
                FROM {INGEST_TABLE}
                WHERE source_hash = ?
                ORDER BY id DESC
                LIMIT 1;
                """,
                (zip_hash,),
            ).fetchone()
            if not source_row:
                return None
            ingest_id, source_name, file_count, total_uncompressed, total_compressed = source_row

            project_rows = conn.execute(
                f"""
                SELECT p.project_name, pi.id
                FROM {PROJECTS_TABLE} p
                JOIN {PROJECT_INFO_TABLE} pi ON pi.project_id = p.id
                WHERE p.source_hash = ? AND pi.ingest_id = ?
                ORDER BY p.project_name ASC;
                """,
                (zip_hash, ingest_id),
            ).fetchall()
            projects: Dict[str, Any] = {}
            for project_name, project_info_id in project_rows:
                projects[project_name] = self._build_project_payload(
                    conn,
                    project_info_id,
                    include_global_insights=False,
                )

            report = {
                "zip_hash": zip_hash,
                "zip_metadata": {
                    "root_name": source_name,
                    "file_count": file_count,
                    "total_uncompressed_bytes": total_uncompressed,
                    "total_compressed_bytes": total_compressed,
                },
                "projects": projects,
            }
            global_insights = self._load_global_insights(conn, ingest_id)
            if global_insights:
                report["global_insights"] = global_insights
            return report

    def list_recent_zipfiles(self, limit: int = 10) -> List[Dict[str, Any]]:
        results = []
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT i.id, i.source_hash, i.source_path, i.created_at, i.updated_at, i.pipeline_version, i.started_at
                FROM {INGEST_TABLE} i
                WHERE i.id = (
                    SELECT id FROM {INGEST_TABLE} i2
                    WHERE i2.source_hash = i.source_hash
                    ORDER BY i2.id DESC
                    LIMIT 1
                )
                ORDER BY i.id DESC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()
            for row in rows:
                ingest_id, source_hash, source_path, created_at, updated_at, pipeline_version, _started_at = row
                project_count = conn.execute(
                    f"SELECT COUNT(*) FROM {PROJECT_INFO_TABLE} WHERE ingest_id = ?;",
                    (ingest_id,),
                ).fetchone()[0]
                results.append(
                    {
                        "zip_hash": source_hash,
                        "zip_path": source_path,
                        "total_projects": project_count,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "pipeline_version": pipeline_version,
                    }
                )
        return results

    def get_zip_metadata(self, zip_hash: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a stored zip hash."""
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT source_name, file_count, total_uncompressed_bytes, total_compressed_bytes
                FROM {INGEST_TABLE}
                WHERE source_hash = ?
                ORDER BY id DESC
                LIMIT 1;
                """,
                (zip_hash,),
            ).fetchone()
            if not row:
                return None
            return {
                "root_name": row[0],
                "file_count": row[1],
                "total_uncompressed_bytes": row[2],
                "total_compressed_bytes": row[3],
            }

    def list_projects_for_zip(self, zip_hash: str) -> List[str]:
        """Return sorted project names associated with the provided zip hash (latest run)."""
        with self._connect() as conn:
            ingest_id = self._latest_ingest_id(conn, zip_hash)
            if not ingest_id:
                return []
            rows = conn.execute(
                f"""
                SELECT p.project_name
                FROM {PROJECTS_TABLE} p
                JOIN {PROJECT_INFO_TABLE} pi ON pi.project_id = p.id
                WHERE p.source_hash = ? AND pi.ingest_id = ?
                ORDER BY p.project_name ASC;
                """,
                (zip_hash, ingest_id),
            ).fetchall()
        return [row[0] for row in rows]

   
    # Deletion API
    def _audit(self, conn: sqlite3.Connection, action: str, scope: str, details: Optional[Dict[str, Any]], deleted_projects: int, deleted_zips: int) -> None:
        conn.execute(
            f"""
            INSERT INTO {DELETION_AUDIT_TABLE} (action, scope, details, deleted_projects, deleted_zips, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (action, scope, json.dumps(details or {}), deleted_projects, deleted_zips, _utcnow()),
        )

    def delete_all(self) -> Dict[str, int]:
        """Hard-delete all insights (irreversible). Returns counts."""
        with self._lock:
            with self._connect() as conn:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    zcount = conn.execute(
                        f"SELECT COUNT(DISTINCT source_hash) FROM {INGEST_TABLE};"
                    ).fetchone()[0]
                    pcount = conn.execute(f"SELECT COUNT(*) FROM {PROJECT_INFO_TABLE};").fetchone()[0]
                    conn.execute(f"DELETE FROM {INGEST_TABLE};")  # cascades project_info/file_info/etc
                    conn.execute(f"DELETE FROM {PROJECTS_TABLE};")
                    conn.execute(f"DELETE FROM {LEGACY_ZIP_TABLE};")
                    self._audit(conn, action="delete_all", scope="all", details=None, deleted_projects=pcount, deleted_zips=zcount)
                    conn.execute("COMMIT;")
                    return {"deleted_projects": pcount, "deleted_zips": zcount}
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

    def delete_zip(self, zip_hash: str) -> Dict[str, int]:
        """Hard-delete a specific stored run by zip_hash. Preserves other runs."""
        with self._lock:
            with self._connect() as conn:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    row = conn.execute(
                        f"SELECT COUNT(*) FROM {INGEST_TABLE} WHERE source_hash = ?;",
                        (zip_hash,),
                    ).fetchone()
                    if not row or row[0] == 0:
                        conn.execute("ROLLBACK;")
                        return {"deleted_projects": 0, "deleted_zips": 0}
                    pcount = conn.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM {PROJECT_INFO_TABLE} pi
                        JOIN {PROJECTS_TABLE} p ON p.id = pi.project_id
                        WHERE p.source_hash = ?;
                        """,
                        (zip_hash,),
                    ).fetchone()[0]
                    conn.execute(f"DELETE FROM {INGEST_TABLE} WHERE source_hash = ?;", (zip_hash,))
                    conn.execute(f"DELETE FROM {PROJECTS_TABLE} WHERE source_hash = ?;", (zip_hash,))
                    self._audit(conn, action="delete_zip", scope=zip_hash, details={"source_hash": zip_hash}, deleted_projects=pcount, deleted_zips=1)
                    conn.execute("COMMIT;")
                    return {"deleted_projects": pcount, "deleted_zips": 1}
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

    def delete_project(self, zip_hash: str, project_name: str) -> Dict[str, int]:
        """Hard-delete a single project under a given zip. Cleans up zip if empty."""
        with self._lock:
            with self._connect() as conn:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    row = conn.execute(
                        f"SELECT COUNT(*) FROM {INGEST_TABLE} WHERE source_hash = ?;",
                        (zip_hash,),
                    ).fetchone()
                    if not row or row[0] == 0:
                        conn.execute("ROLLBACK;")
                        return {"deleted_projects": 0, "deleted_zips": 0}
                    prow = conn.execute(
                        f"SELECT id FROM {PROJECTS_TABLE} WHERE source_hash = ? AND project_name = ?;",
                        (zip_hash, project_name),
                    ).fetchone()
                    if not prow:
                        conn.execute("ROLLBACK;")
                        return {"deleted_projects": 0, "deleted_zips": 0}
                    project_id = prow[0]
                    pcount = conn.execute(
                        f"SELECT COUNT(*) FROM {PROJECT_INFO_TABLE} WHERE project_id = ?;",
                        (project_id,),
                    ).fetchone()[0]
                    conn.execute(f"DELETE FROM {PROJECTS_TABLE} WHERE id = ?;", (project_id,))
                    remaining = conn.execute(
                        f"SELECT COUNT(*) FROM {PROJECTS_TABLE} WHERE source_hash = ?;",
                        (zip_hash,),
                    ).fetchone()[0]
                    zdel = 0
                    if remaining == 0:
                        conn.execute(f"DELETE FROM {INGEST_TABLE} WHERE source_hash = ?;", (zip_hash,))
                        zdel = 1
                    self._audit(conn, action="delete_project", scope=f"{zip_hash}:{project_name}", details={"source_hash": zip_hash}, deleted_projects=pcount, deleted_zips=zdel)
                    conn.execute("COMMIT;")
                    return {"deleted_projects": pcount, "deleted_zips": zdel}
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise

    def backup(self, backup_path: str) -> str:
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database does not exist at {self.db_path}")
        target = Path(backup_path)
        if target.is_dir():
            target = target / f"insights_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        _ensure_parent(str(target))
        shutil.copy2(self.db_path, target)
        self._mark_backup()
        return str(target)

    def restore(self, backup_path: str) -> None:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        _ensure_parent(self.db_path)
        temp_target = f"{self.db_path}.restoring"
        shutil.copy2(backup_path, temp_target)
        shutil.move(temp_target, self.db_path)
        self._apply_migrations()

    def purge_expired_records(self, retention_days: int, keep_recent: int = 5) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT i.id, i.source_hash, i.updated_at
                    FROM {INGEST_TABLE} i
                    WHERE i.id = (
                        SELECT id FROM {INGEST_TABLE} i2
                        WHERE i2.source_hash = i.source_hash
                        ORDER BY i2.id DESC
                        LIMIT 1
                    )
                    ORDER BY datetime(i.updated_at) DESC;
                    """
                ).fetchall()
                keep_hashes = {row[1] for row in rows[:keep_recent]}
                purge_hashes: List[str] = []
                for _id, source_hash, updated_at_raw in rows:
                    if source_hash in keep_hashes:
                        continue
                    updated_at = _iso_to_datetime(updated_at_raw)
                    if updated_at < cutoff:
                        purge_hashes.append(source_hash)
                if not purge_hashes:
                    return 0
                placeholders = ",".join("?" for _ in purge_hashes)
                conn.execute(
                    f"DELETE FROM {INGEST_TABLE} WHERE source_hash IN ({placeholders});",
                    purge_hashes,
                )
                conn.execute(
                    f"DELETE FROM {PROJECTS_TABLE} WHERE source_hash IN ({placeholders});",
                    purge_hashes,
                )
                conn.commit()
        return len(purge_hashes)

    # Internal helpers
    def _validate_pipeline_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise PayloadValidationError("Pipeline output must be a dict.")
        metadata = payload.get("zip_metadata")
        if not isinstance(metadata, dict):
            raise PayloadValidationError("zip_metadata is required.")
        expected_meta = {"root_name", "file_count", "total_uncompressed_bytes", "total_compressed_bytes"}
        missing = [field for field in expected_meta if field not in metadata]
        if missing:
            raise PayloadValidationError(f"Missing metadata fields: {', '.join(missing)}")
        projects = payload.get("projects")
        if not isinstance(projects, dict) or not projects:
            raise PayloadValidationError("projects payload must be a non-empty mapping.")
        cleaned: Dict[str, Dict[str, Any]] = {}
        for name, data in projects.items():
            if not isinstance(data, dict):
                continue
            cleaned[name] = data
        if not cleaned:
            raise PayloadValidationError("No valid project payloads found.")
        extras = {k: v for k, v in payload.items() if k not in {"zip_metadata", "projects"}}
        return {"zip_metadata": metadata, "projects": cleaned, "extras": extras}

    def _derive_zip_hash(self, zip_path: str, metadata: Dict[str, Any]) -> str:
        hasher = hashlib.sha256()
        hasher.update(Path(zip_path).name.encode("utf-8"))
        hasher.update(str(metadata.get("file_count", 0)).encode("utf-8"))
        hasher.update(str(metadata.get("total_uncompressed_bytes", 0)).encode("utf-8"))
        hasher.update(str(metadata.get("total_compressed_bytes", 0)).encode("utf-8"))
        return hasher.hexdigest()

    def _slugify(self, name: str) -> str:
        safe = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
        return "-".join(filter(None, safe.split("-")))[:128] or "project"

    def _normalize_path(self, path: str, root: Optional[str]) -> str:
        if not path:
            return ""
        p = Path(path)
        if root:
            try:
                return p.relative_to(Path(root)).as_posix()
            except ValueError:
                pass
        return p.as_posix()

    def _build_file_info_lookup(self, extras: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        entries = extras.get("file_info")
        if not isinstance(entries, list):
            return {}
        lookup: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            abs_path = entry.get("abs_path")
            if not abs_path:
                continue
            try:
                lookup[str(Path(abs_path).resolve())] = entry
            except Exception:
                lookup[abs_path] = entry
        return lookup

    def _lookup_file_info(
        self,
        lookup: Optional[Dict[str, Dict[str, Any]]],
        file_path: str,
    ) -> Optional[Dict[str, Any]]:
        if not lookup:
            return None
        if file_path in lookup:
            return lookup[file_path]
        try:
            resolved = str(Path(file_path).resolve())
        except Exception:
            return None
        return lookup.get(resolved)

    def _latest_ingest_id(self, conn: sqlite3.Connection, source_hash: str) -> Optional[int]:
        row = conn.execute(
            f"""
            SELECT id FROM {INGEST_TABLE}
            WHERE source_hash = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (source_hash,),
        ).fetchone()
        return row[0] if row else None

    def _insert_ingest_run(
        self,
        conn: sqlite3.Connection,
        source_hash: str,
        source_path: str,
        metadata: Dict[str, Any],
        pipeline_version: str,
        timestamp: str,
    ) -> Tuple[int, bool]:
        source_name = metadata.get("root_name") or Path(source_path).name
        file_count = int(metadata.get("file_count", 0))
        total_uncompressed = int(metadata.get("total_uncompressed_bytes", 0))
        total_compressed = int(metadata.get("total_compressed_bytes", 0))
        row = conn.execute(
            f"""
            SELECT source_name, file_count, total_uncompressed_bytes, total_compressed_bytes
            FROM {INGEST_TABLE}
            WHERE source_hash = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (source_hash,),
        ).fetchone()
        metadata_updated = True
        if row:
            existing_name, existing_files, existing_uncompressed, existing_compressed = row
            metadata_updated = (
                existing_name != source_name
                or existing_files != file_count
                or existing_uncompressed != total_uncompressed
                or existing_compressed != total_compressed
            )
        conn.execute(
            f"""
            INSERT INTO {INGEST_TABLE} (
                source_type, source_path, source_name, source_hash,
                file_count, total_uncompressed_bytes, total_compressed_bytes,
                run_type, parent_run_id, pipeline_version, status,
                started_at, finished_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "zip",
                source_path,
                source_name,
                source_hash,
                file_count,
                total_uncompressed,
                total_compressed,
                "full",
                None,
                pipeline_version,
                "completed",
                timestamp,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        ingest_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]
        return ingest_id, metadata_updated

    def _upsert_project(
        self,
        conn: sqlite3.Connection,
        source_hash: str,
        project_name: str,
        project_payload: Dict[str, Any],
        timestamp: str,
    ) -> int:
        project_key = project_name
        slug = self._slugify(project_name)
        root_path = project_payload.get("project_path")
        row = conn.execute(
            f"""
            SELECT id FROM {PROJECTS_TABLE}
            WHERE source_hash = ? AND project_key = ?;
            """,
            (source_hash, project_key),
        ).fetchone()
        if row:
            project_id = row[0]
            conn.execute(
                f"""
                UPDATE {PROJECTS_TABLE}
                SET project_name = ?, slug = ?, root_path = ?, updated_at = ?
                WHERE id = ?;
                """,
                (project_name, slug, root_path, timestamp, project_id),
            )
            return project_id
        conn.execute(
            f"""
            INSERT INTO {PROJECTS_TABLE} (
                source_hash, project_key, project_name, slug, root_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (source_hash, project_key, project_name, slug, root_path, timestamp, timestamp),
        )
        return conn.execute("SELECT last_insert_rowid();").fetchone()[0]

    def _insert_project_info(
        self,
        conn: sqlite3.Connection,
        project_id: int,
        ingest_id: int,
        project_name: str,
        project_payload: Dict[str, Any],
        timestamp: str,
    ) -> int:
        project_name_value = project_payload.get("project_name") or project_name
        project_path = project_payload.get("project_path")
        is_git_repo = 1 if project_payload.get("is_git_repo") else 0
        conn.execute(
            f"""
            INSERT INTO {PROJECT_INFO_TABLE} (
                project_id, ingest_id, project_name, project_path, is_git_repo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                project_id,
                ingest_id,
                project_name_value,
                project_path,
                is_git_repo,
                timestamp,
                timestamp,
            ),
        )
        return conn.execute("SELECT last_insert_rowid();").fetchone()[0]

    def _get_or_create_file_id(
        self,
        conn: sqlite3.Connection,
        project_id: int,
        rel_path: str,
        timestamp: str,
    ) -> int:
        row = conn.execute(
            f"""
            SELECT id FROM {FILES_TABLE}
            WHERE project_id = ? AND relative_path = ?;
            """,
            (project_id, rel_path),
        ).fetchone()
        if row:
            return row[0]
        file_name = Path(rel_path).name
        extension = Path(rel_path).suffix.lower() or None
        conn.execute(
            f"""
            INSERT INTO {FILES_TABLE} (project_id, relative_path, file_name, extension, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (project_id, rel_path, file_name, extension, timestamp),
        )
        return conn.execute("SELECT last_insert_rowid();").fetchone()[0]

    def _append_file_metric(
        self,
        metrics: List[Dict[str, Any]],
        namespace: str,
        key: str,
        value_text: Optional[str] = None,
        value_num: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> None:
        metrics.append(
            {
                "namespace": namespace,
                "key": key,
                "value_text": value_text,
                "value_num": value_num,
                "unit": unit,
            }
        )

    def _ensure_tag_id(
        self,
        conn: sqlite3.Connection,
        tag_type: str,
        name: str,
        category: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> int:
        row = conn.execute(
            f"SELECT id FROM {TAGS_TABLE} WHERE tag_type = ? AND name = ?;",
            (tag_type, name),
        ).fetchone()
        if row:
            return row[0]
        created_at = timestamp or _utcnow()
        conn.execute(
            f"INSERT INTO {TAGS_TABLE} (tag_type, name, category, created_at) VALUES (?, ?, ?, ?);",
            (tag_type, name, category, created_at),
        )
        return conn.execute("SELECT last_insert_rowid();").fetchone()[0]

    def _build_analysis_map(self, items: List[Dict[str, Any]], project_root: Optional[str]) -> Dict[str, Dict[str, Any]]:
        mapping: Dict[str, Dict[str, Any]] = {}
        for item in items:
            file_path = item.get("file_path")
            if not file_path:
                continue
            rel_path = self._normalize_path(file_path, project_root)
            mapping[rel_path] = item
        return mapping

    def _store_project_files_and_analysis(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_id: int,
        project_payload: Dict[str, Any],
        timestamp: str,
        file_info_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        categorized = project_payload.get("categorized_contents") or {}
        analysis = project_payload.get("analysis_results") or {}
        project_root = project_payload.get("project_path")

        language_map: Dict[str, str] = {}
        for lang, paths in (categorized.get("code_by_language") or {}).items():
            for path in paths or []:
                rel = self._normalize_path(path, project_root)
                language_map[rel] = lang

        code_analysis = {}
        skill_analysis = {}
        code_block = analysis.get("code")
        if isinstance(code_block, dict) and "error" not in code_block:
            code_analysis = self._build_analysis_map(code_block.get("files", []) or [], project_root)
            skill_block = code_block.get("skill_analysis", {}) or {}
            skill_analysis = self._build_analysis_map(skill_block.get("per_file", []) or [], project_root)

        doc_analysis = {}
        doc_block = analysis.get("documentation")
        if isinstance(doc_block, dict) and "error" not in doc_block:
            doc_analysis = self._build_analysis_map(doc_block.get("files", []) or [], project_root)

        image_analysis = {}
        image_block = analysis.get("images")
        if isinstance(image_block, list):
            image_analysis = self._build_analysis_map(image_block, project_root)

        video_analysis = {}
        video_block = analysis.get("videos")
        if isinstance(video_block, dict) and "error" not in video_block:
            video_analysis = self._build_analysis_map(video_block.get("files", []) or [], project_root)

        file_entries: Dict[str, str] = {}
        for category_key, default_category in (
            ("code", "code"),
            ("documentation", "documentation"),
            ("images", "images"),
            ("sketches", "other"),
            ("other", "other"),
        ):
            for path in categorized.get(category_key, []) or []:
                if path and path not in file_entries:
                    file_entries[path] = default_category

        path_lookup: Dict[str, int] = {}
        for file_path, category in file_entries.items():
            rel_path = self._normalize_path(file_path, project_root)
            file_id = self._get_or_create_file_id(conn, project_id, rel_path, timestamp)
            resolved_category = category
            if category == "other" and Path(file_path).suffix.lower() in ArtifactVideoHint.EXTENSIONS:
                resolved_category = "video"

            language = None
            code_item = code_analysis.get(rel_path)
            if code_item:
                language = code_item.get("language")
            if not language:
                language = language_map.get(rel_path)

            info = self._lookup_file_info(file_info_lookup, file_path)
            size_bytes: Optional[int] = None
            modified_at = None
            is_binary = 0
            content_hash = None
            if info:
                if info.get("is_text_guess") is False:
                    is_binary = 1
                if info.get("size") is not None:
                    try:
                        size_bytes = int(info.get("size", 0))
                    except (TypeError, ValueError):
                        size_bytes = None
                content_hash = info.get("sha256")
            try:
                stat = Path(file_path).stat()
                if size_bytes is None:
                    size_bytes = int(stat.st_size)
                modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            except Exception:
                size_bytes = size_bytes or 0
            metrics: List[Dict[str, Any]] = []
            tags: List[Dict[str, Any]] = []
            evidence_rows: List[Tuple[int, Dict[str, Any]]] = []

            if code_item:
                self._append_file_metric(
                    metrics,
                    "code",
                    "analysis_json",
                    value_text=json.dumps(code_item),
                )
                self._append_file_metric(
                    metrics,
                    "code",
                    "lines_of_code",
                    value_num=code_item.get("lines_of_code", 0),
                )
                self._append_file_metric(
                    metrics,
                    "code",
                    "file_type",
                    value_text=code_item.get("file_type"),
                )
                for fw in code_item.get("frameworks", []) or []:
                    tag_id = self._ensure_tag_id(conn, "framework", str(fw), timestamp=timestamp)
                    tags.append({"tag_id": tag_id, "tag_type": "framework", "name": str(fw), "score": None})
                for skill in code_item.get("skills", []) or []:
                    tag_id = self._ensure_tag_id(conn, "skill", str(skill), timestamp=timestamp)
                    tags.append({"tag_id": tag_id, "tag_type": "skill", "name": str(skill), "score": None})

            skill_item = skill_analysis.get(rel_path)
            if skill_item:
                self._append_file_metric(
                    metrics,
                    "code",
                    "skill_analysis_json",
                    value_text=json.dumps(skill_item),
                )
                for ev in skill_item.get("evidence", []) or []:
                    skill_name = ev.get("skill")
                    if not skill_name:
                        continue
                    tag_id = self._ensure_tag_id(conn, "skill", str(skill_name), timestamp=timestamp)
                    evidence_rows.append(
                        (
                            tag_id,
                            {
                                "type": ev.get("type"),
                                "location": ev.get("location"),
                                "reasoning": ev.get("reasoning"),
                            },
                        )
                    )

            doc_item = doc_analysis.get(rel_path)
            if doc_item:
                self._append_file_metric(
                    metrics,
                    "text",
                    "analysis_json",
                    value_text=json.dumps(doc_item),
                )

            img_item = image_analysis.get(rel_path)
            if img_item:
                self._append_file_metric(
                    metrics,
                    "image",
                    "analysis_json",
                    value_text=json.dumps(img_item),
                )

            vid_item = video_analysis.get(rel_path)
            if vid_item:
                self._append_file_metric(
                    metrics,
                    "video",
                    "analysis_json",
                    value_text=json.dumps(vid_item),
                )

            metrics_json = json.dumps(metrics) if metrics else None
            tags_json = json.dumps(tags) if tags else None

            conn.execute(
                f"""
                INSERT INTO {FILE_INFO_TABLE} (
                    file_id, project_info_id, content_hash, content_size_bytes, content_mime_type,
                    size_bytes, modified_at, is_binary, is_deleted, language, category,
                    metrics_json, tags_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    file_id,
                    project_info_id,
                    str(content_hash) if content_hash else None,
                    int(size_bytes or 0),
                    None,
                    int(size_bytes or 0),
                    modified_at,
                    is_binary,
                    0,
                    language,
                    resolved_category,
                    metrics_json,
                    tags_json,
                    timestamp,
                ),
            )
            file_info_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]
            path_lookup[file_path] = file_info_id
            try:
                path_lookup[str(Path(file_path).resolve())] = file_info_id
            except Exception:
                pass
            path_lookup[rel_path] = file_info_id

            for tag_id, ev in evidence_rows:
                conn.execute(
                    f"""
                    INSERT INTO {SKILL_EVIDENCE_TABLE} (
                        project_info_id, file_info_id, tag_id, evidence_type, location, reasoning, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        project_info_id,
                        file_info_id,
                        tag_id,
                        ev.get("type"),
                        ev.get("location"),
                        ev.get("reasoning"),
                        None,
                    ),
                )

        return path_lookup

    def _store_project_metrics(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_payload: Dict[str, Any],
        timestamp: str,
    ) -> None:
        metrics = project_payload.get("project_metrics") or {}
        git_analysis = project_payload.get("git_analysis") or {}
        if not metrics:
            analysis = project_payload.get("analysis_results") or {}
            code_block = analysis.get("code") if isinstance(analysis, dict) else None
            code_metrics = code_block.get("metrics", {}) if isinstance(code_block, dict) else {}
            doc_block = analysis.get("documentation") if isinstance(analysis, dict) else None
            doc_totals = doc_block.get("totals", {}) if isinstance(doc_block, dict) else {}
            categorized = project_payload.get("categorized_contents") or {}
            video_files = [
                p
                for p in categorized.get("other", []) or []
                if Path(p).suffix.lower() in ArtifactVideoHint.EXTENSIONS
            ]
            metrics = {
                "total_files": code_metrics.get("total_files", 0),
                "total_lines": code_metrics.get("total_lines", 0),
                "test_files": code_metrics.get("test_files", 0),
                "doc_files": doc_totals.get("total_files", 0),
                "doc_words": doc_totals.get("total_words", 0),
                "image_files": len(categorized.get("images", []) or []),
                "video_files": len(video_files),
                "has_documentation": bool(doc_totals.get("total_files")),
                "has_tests": bool(code_metrics.get("test_files")),
                "has_images": bool(categorized.get("images")),
                "has_videos": bool(video_files),
                "languages": code_metrics.get("languages", []) or [],
                "frameworks": code_metrics.get("frameworks", []) or [],
                "skills": code_metrics.get("skills", []) or [],
            }
        activity = git_analysis.get("activity_mix") or {}
        duration_start = git_analysis.get("first_commit_at") or git_analysis.get("start")
        duration_end = git_analysis.get("last_commit_at") or git_analysis.get("end")
        duration_days = git_analysis.get("duration_days") or 0
        languages_json = json.dumps(metrics.get("languages", []) or [])
        frameworks_json = json.dumps(metrics.get("frameworks", []) or [])
        skills_json = json.dumps(metrics.get("skills", []) or [])
        conn.execute(
            f"""
            UPDATE {PROJECT_INFO_TABLE}
            SET total_files = ?, total_lines = ?, total_commits = ?, total_contributors = ?,
                activity_code = ?, activity_test = ?, activity_doc = ?, duration_start = ?, duration_end = ?,
                duration_days = ?, doc_files = ?, doc_words = ?, image_files = ?, video_files = ?, test_files = ?,
                has_documentation = ?, has_tests = ?, has_images = ?, has_videos = ?,
                languages_json = ?, frameworks_json = ?, skills_json = ?, updated_at = ?
            WHERE id = ?;
            """,
            (
                int(metrics.get("total_files", 0)),
                int(metrics.get("total_lines", 0)),
                int(metrics.get("total_commits", git_analysis.get("total_commits", 0) or 0)),
                int(metrics.get("total_contributors", git_analysis.get("total_contributors", 0) or 0)),
                int(activity.get("code", 0) or 0),
                int(activity.get("test", 0) or 0),
                int(activity.get("doc", 0) or 0),
                duration_start,
                duration_end,
                int(duration_days or 0),
                int(metrics.get("doc_files", 0)),
                int(metrics.get("doc_words", 0)),
                int(metrics.get("image_files", 0)),
                int(metrics.get("video_files", 0)),
                int(metrics.get("test_files", 0)),
                1 if metrics.get("has_documentation") else 0,
                1 if metrics.get("has_tests") else 0,
                1 if metrics.get("has_images") else 0,
                1 if metrics.get("has_videos") else 0,
                languages_json,
                frameworks_json,
                skills_json,
                timestamp,
                project_info_id,
            ),
        )

    def _store_project_contributors(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_payload: Dict[str, Any],
        timestamp: str,
    ) -> None:
        git_analysis = project_payload.get("git_analysis") or {}
        contributors = git_analysis.get("contributors") or []
        contributor_rows: List[Dict[str, Any]] = []
        for contributor in contributors:
            author = contributor.get("author") or {}
            contributor_rows.append(
                {
                    "author": {
                        "name": author.get("name") or contributor.get("name") or "Unknown",
                        "email": author.get("email") or contributor.get("email"),
                    },
                    "commits": int(contributor.get("commits", 0) or 0),
                }
            )
        contributor_rows.sort(key=lambda row: row.get("commits", 0), reverse=True)
        conn.execute(
            f"""
            UPDATE {PROJECT_INFO_TABLE}
            SET contributors_json = ?, updated_at = ?
            WHERE id = ?;
            """,
            (json.dumps(contributor_rows), timestamp, project_info_id),
        )

    def _store_project_tags(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_payload: Dict[str, Any],
        timestamp: str,
    ) -> None:
        metrics = project_payload.get("project_metrics") or {}
        if not metrics:
            analysis = project_payload.get("analysis_results") or {}
            code_block = analysis.get("code") if isinstance(analysis, dict) else None
            code_metrics = code_block.get("metrics", {}) if isinstance(code_block, dict) else {}
            metrics = {
                "languages": code_metrics.get("languages", []) or [],
                "frameworks": code_metrics.get("frameworks", []) or [],
                "skills": code_metrics.get("skills", []) or [],
            }
        tags: List[Dict[str, Any]] = []
        for tag_type, values in (
            ("language", metrics.get("languages", []) or []),
            ("framework", metrics.get("frameworks", []) or []),
            ("skill", metrics.get("skills", []) or []),
        ):
            for order, value in enumerate(values):
                tag_id = self._ensure_tag_id(conn, tag_type, str(value), timestamp=timestamp)
                tags.append(
                    {
                        "tag_id": tag_id,
                        "tag_type": tag_type,
                        "name": str(value),
                        "source": "local",
                        "score": None,
                        "display_order": order,
                        "is_highlighted": 0,
                    }
                )

        keyword_tags: List[str] = []
        doc_block = (project_payload.get("analysis_results") or {}).get("documentation")
        if isinstance(doc_block, dict):
            totals = doc_block.get("totals") or {}
            keywords = totals.get("top_keywords_overall") or []
            for order, item in enumerate(keywords):
                word = item[0] if isinstance(item, (list, tuple)) else item
                if not word:
                    continue
                keyword_tags.append(str(word))
                tag_id = self._ensure_tag_id(conn, "keyword", str(word), timestamp=timestamp)
                tags.append(
                    {
                        "tag_id": tag_id,
                        "tag_type": "keyword",
                        "name": str(word),
                        "source": "local",
                        "score": None,
                        "display_order": order,
                        "is_highlighted": 0,
                    }
                )

        conn.execute(
            f"""
            UPDATE {PROJECT_INFO_TABLE}
            SET tags_json = ?, keyword_tags_json = ?, updated_at = ?
            WHERE id = ?;
            """,
            (json.dumps(tags) if tags else None, json.dumps(keyword_tags), timestamp, project_info_id),
        )

    def _store_portfolio_insights(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_payload: Dict[str, Any],
        pipeline_version: str,
        timestamp: str,
    ) -> None:
        portfolio_item = project_payload.get("portfolio_item") or {}
        resume_item = project_payload.get("resume_item") or {}
        if isinstance(portfolio_item, dict) and "error" in portfolio_item:
            portfolio_item = {}
        if isinstance(resume_item, dict) and "error" in resume_item:
            resume_item = {}
        if not portfolio_item and not resume_item:
            return

        conn.execute(
            f"""
            INSERT INTO {PORTFOLIO_INSIGHTS_TABLE} (
                project_info_id, generated_at, pipeline_version, tagline, description,
                project_type, complexity, is_collaborative, summary, key_features_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                project_info_id,
                timestamp,
                pipeline_version,
                portfolio_item.get("tagline"),
                portfolio_item.get("description"),
                portfolio_item.get("project_type"),
                portfolio_item.get("complexity"),
                1 if portfolio_item.get("is_collaborative") else 0,
                portfolio_item.get("summary"),
                json.dumps(portfolio_item.get("key_features", []) or []),
            ),
        )
        insight_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]

        for order, bullet in enumerate(resume_item.get("bullets", []) or []):
            conn.execute(
                f"""
                INSERT INTO {RESUME_BULLETS_TABLE} (
                    portfolio_insight_id, bullet_text, display_order, is_selected, source
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (insight_id, str(bullet), order, 1, "generated"),
            )

    def _store_global_insights(
        self,
        conn: sqlite3.Connection,
        ingest_id: int,
        extras: Dict[str, Any],
        timestamp: str,
    ) -> None:
        ranking = extras.get("project_ranking") or extras.get("ranking_results")
        if isinstance(ranking, dict) and ranking:
            criteria = "score"
            summaries = ranking.get("top_summaries") or []
            if summaries:
                criteria = summaries[0].get("criteria") or criteria
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {RANKING_TABLE} (ingest_id, criteria, created_at, ranking_json)
                VALUES (?, ?, ?, ?);
                """,
                (ingest_id, criteria, timestamp, json.dumps(ranking)),
            )

        chronology = extras.get("chronological_skills") or {}
        if isinstance(chronology, dict) and chronology:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {CHRONOLOGY_TABLE} (ingest_id, chronology_json, created_at)
                VALUES (?, ?, ?);
                """,
                (ingest_id, json.dumps(chronology), timestamp),
            )

    def _build_project_payload(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        include_global_insights: bool = True,
    ) -> Dict[str, Any]:
        row = conn.execute(
            f"""
            SELECT pi.project_id, pi.project_path, pi.is_git_repo, pi.ingest_id, p.project_name, p.root_path, pi.project_name
            FROM {PROJECT_INFO_TABLE} pi
            JOIN {PROJECTS_TABLE} p ON p.id = pi.project_id
            WHERE pi.id = ?;
            """,
            (project_info_id,),
        ).fetchone()
        if not row:
            return {}
        project_id, project_path, is_git_repo, ingest_id, stored_name, root_path, project_name_override = row
        project_name = project_name_override or stored_name

        categorized, file_revision_ids, file_rev_to_path = self._load_categorized_contents(
            conn,
            project_info_id,
        )
        project_metrics = self._load_project_metrics(conn, project_info_id)
        analysis_results = self._load_analysis_results(
            conn,
            file_revision_ids,
            file_rev_to_path,
            categorized,
            project_metrics,
        )
        portfolio_item, resume_item = self._load_presentation_items(conn, project_info_id, project_name, project_metrics)
        git_analysis = self._load_git_analysis(conn, project_info_id, project_metrics)
        global_insights = self._load_global_insights(conn, ingest_id) if include_global_insights else {}

        payload = {
            "project_name": project_name,
            "project_path": project_path or root_path,
            "is_git_repo": bool(is_git_repo),
            "git_analysis": git_analysis,
            "categorized_contents": categorized,
            "analysis_results": analysis_results,
            "project_metrics": project_metrics,
            "portfolio_item": portfolio_item,
            "resume_item": resume_item,
        }
        if global_insights:
            payload["global_insights"] = global_insights
        return payload

    def _load_categorized_contents(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
    ) -> Tuple[Dict[str, Any], List[int], Dict[int, str]]:
        rows = conn.execute(
            f"""
            SELECT fi.id, f.relative_path, f.extension, fi.category, fi.language
            FROM {FILE_INFO_TABLE} fi
            JOIN {FILES_TABLE} f ON f.id = fi.file_id
            WHERE fi.project_info_id = ?;
            """,
            (project_info_id,),
        ).fetchall()
        categorized = {
            "code": [],
            "code_by_language": {},
            "documentation": [],
            "images": [],
            "sketches": [],
            "other": [],
        }
        file_revision_ids: List[int] = []
        file_rev_to_path: Dict[int, str] = {}
        sketch_exts = {".drawio", ".vsdx", ".sketch", ".fig", ".xd"}
        for file_revision_id, rel_path, extension, category, language in rows:
            file_revision_ids.append(file_revision_id)
            file_rev_to_path[file_revision_id] = rel_path
            ext = (extension or Path(rel_path).suffix).lower()
            if category == "code":
                categorized["code"].append(rel_path)
                lang = language or ext.lstrip(".") or "unknown"
                categorized["code_by_language"].setdefault(lang, []).append(rel_path)
            elif category == "documentation":
                categorized["documentation"].append(rel_path)
            elif category == "images":
                categorized["images"].append(rel_path)
            else:
                if ext in sketch_exts:
                    categorized["sketches"].append(rel_path)
                else:
                    categorized["other"].append(rel_path)
        return categorized, file_revision_ids, file_rev_to_path

    def _fetch_metric_json(
        self,
        conn: sqlite3.Connection,
        file_revision_ids: List[int],
        namespace: str,
        key: str,
    ) -> Dict[int, Dict[str, Any]]:
        if not file_revision_ids:
            return {}
        placeholders = ",".join("?" for _ in file_revision_ids)
        rows = conn.execute(
            f"""
            SELECT id, metrics_json
            FROM {FILE_INFO_TABLE}
            WHERE id IN ({placeholders});
            """,
            (*file_revision_ids,),
        ).fetchall()
        out: Dict[int, Dict[str, Any]] = {}
        for file_info_id, metrics_json in rows:
            if not metrics_json:
                continue
            try:
                metrics = json.loads(metrics_json)
            except Exception:
                continue
            for entry in metrics:
                if entry.get("namespace") != namespace or entry.get("key") != key:
                    continue
                value_text = entry.get("value_text")
                if value_text is None and entry.get("value_num") is not None:
                    out[file_info_id] = {"value": entry.get("value_num")}
                    continue
                if not value_text:
                    continue
                try:
                    out[file_info_id] = json.loads(value_text)
                except Exception:
                    out[file_info_id] = {"raw": value_text}
                break
        return out

    def _load_analysis_results(
        self,
        conn: sqlite3.Connection,
        file_revision_ids: List[int],
        file_rev_to_path: Dict[int, str],
        categorized: Dict[str, Any],
        project_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        analysis_results: Dict[str, Any] = {}

        code_json = self._fetch_metric_json(conn, file_revision_ids, "code", "analysis_json")
        skill_json = self._fetch_metric_json(conn, file_revision_ids, "code", "skill_analysis_json")
        doc_json = self._fetch_metric_json(conn, file_revision_ids, "text", "analysis_json")
        img_json = self._fetch_metric_json(conn, file_revision_ids, "image", "analysis_json")
        vid_json = self._fetch_metric_json(conn, file_revision_ids, "video", "analysis_json")

        # Documentation
        doc_files = [doc_json[rid] for rid in doc_json if rid in file_rev_to_path]
        if doc_files:
            analysis_results["documentation"] = {
                "files": doc_files,
                "totals": self._compute_text_totals(doc_files),
            }
        elif project_metrics.get("doc_files") or categorized.get("documentation"):
            analysis_results["documentation"] = {
                "files": [],
                "totals": {
                    "total_files": project_metrics.get("doc_files", 0),
                    "total_words": project_metrics.get("doc_words", 0),
                },
            }
        else:
            analysis_results["documentation"] = None

        # Images
        img_files = [img_json[rid] for rid in img_json if rid in file_rev_to_path]
        analysis_results["images"] = img_files if img_files else None

        # Code
        code_files = [code_json[rid] for rid in code_json if rid in file_rev_to_path]
        if code_files:
            analysis_results["code"] = {
                "files": code_files,
                "metrics": self._compute_code_metrics(code_files),
                "skill_analysis": self._compute_skill_analysis(skill_json),
            }
        elif categorized.get("code") or project_metrics.get("total_files"):
            analysis_results["code"] = {
                "files": [],
                "metrics": {
                    "total_files": project_metrics.get("total_files", 0),
                    "total_lines": project_metrics.get("total_lines", 0),
                    "languages": project_metrics.get("languages", []),
                    "frameworks": project_metrics.get("frameworks", []),
                    "skills": project_metrics.get("skills", []),
                    "code_files": project_metrics.get("total_files", 0),
                    "test_files": project_metrics.get("test_files", 0),
                },
                "skill_analysis": self._compute_skill_analysis(skill_json),
            }
        else:
            analysis_results["code"] = None

        # Videos
        video_files = [vid_json[rid] for rid in vid_json if rid in file_rev_to_path]
        if video_files:
            analysis_results["videos"] = {
                "files": video_files,
                "metrics": self._compute_video_metrics(video_files),
            }
        elif project_metrics.get("video_files"):
            analysis_results["videos"] = {
                "files": [],
                "metrics": self._compute_video_metrics([]),
            }
        else:
            analysis_results["videos"] = None

        return analysis_results

    def _compute_text_totals(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not files:
            return {}
        total_words = sum(int(f.get("word_count", 0) or 0) for f in files)
        total_sentences = sum(int(f.get("sentence_count", 0) or 0) for f in files)
        total_paragraphs = sum(int(f.get("paragraph_count", 0) or 0) for f in files)
        total_chars = sum(int(f.get("character_count", 0) or 0) for f in files)
        total_size = sum(int(f.get("file_size_bytes", 0) or 0) for f in files)
        total_pages = sum(int(f.get("page_count", 0) or 0) for f in files if f.get("page_count") is not None)
        keyword_counts: Dict[str, int] = {}
        for f in files:
            for word, count in f.get("top_keywords", []) or []:
                keyword_counts[word] = keyword_counts.get(word, 0) + count
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        file_types = {"pdf": 0, "docx": 0, "txt": 0}
        for f in files:
            ftype = f.get("file_type")
            if ftype in file_types:
                file_types[ftype] += 1
        return {
            "total_files": len(files),
            "total_words": total_words,
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
            "total_characters": total_chars,
            "total_size_bytes": total_size,
            "total_pages": total_pages if total_pages > 0 else None,
            "total_reading_time_minutes": round(total_words / 200.0, 2) if total_words else 0,
            "avg_words_per_file": round(total_words / len(files), 2) if files else 0,
            "avg_lexical_diversity": round(
                sum(float(f.get("lexical_diversity", 0) or 0) for f in files) / len(files),
                4,
            )
            if files
            else 0,
            "file_types": file_types,
            "top_keywords_overall": top_keywords,
        }

    def _compute_code_metrics(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_files = len(files)
        total_lines = sum(int(f.get("lines_of_code", 0) or 0) for f in files)
        languages = sorted({f.get("language") for f in files if f.get("language") and f.get("language") != "unknown"})
        frameworks = sorted({fw for f in files for fw in f.get("frameworks", []) or []})
        skills = sorted({skill for f in files for skill in f.get("skills", []) or []})
        code_files = sum(1 for f in files if f.get("file_type") == "code")
        test_files = sum(1 for f in files if f.get("file_type") == "test")
        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "languages": languages,
            "frameworks": frameworks,
            "skills": skills,
            "code_files": code_files,
            "test_files": test_files,
        }

    def _compute_skill_analysis(self, skill_json: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        per_file = list(skill_json.values())
        all_basic = set()
        all_advanced = set()
        all_patterns = set()
        evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for entry in per_file:
            for skill in entry.get("basic_skills", []) or []:
                all_basic.add(skill)
            for skill in entry.get("advanced_skills", []) or []:
                all_advanced.add(skill)
            for skill in entry.get("design_patterns", []) or []:
                all_patterns.add(skill)
            for ev in entry.get("evidence", []) or []:
                skill_name = ev.get("skill")
                if not skill_name:
                    continue
                evidence_by_skill.setdefault(skill_name, []).append(
                    {
                        "type": ev.get("type"),
                        "reasoning": ev.get("reasoning"),
                        "location": ev.get("location"),
                    }
                )
        aggregate = {
            "basic_skills": sorted(all_basic),
            "advanced_skills": sorted(all_advanced),
            "design_patterns": sorted(all_patterns),
            "evidence_count": sum(len(v) for v in evidence_by_skill.values()),
            "evidence_by_skill": evidence_by_skill,
            "total_files_analyzed": len(per_file),
        }
        return {"per_file": per_file, "aggregate": aggregate}

    def _compute_video_metrics(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_videos = len(files)
        total_duration = sum(float(f.get("duration_seconds", 0) or 0) for f in files)
        avg_fps = (
            round(sum(float(f.get("frame_rate", 0) or 0) for f in files) / total_videos, 2)
            if total_videos
            else 0.0
        )
        resolutions = sorted({f.get("resolution") for f in files if f.get("resolution")})
        formats = sorted({f.get("format") for f in files if f.get("format")})
        audio_videos = sum(1 for f in files if f.get("has_audio"))
        video_only = sum(1 for f in files if not f.get("has_audio"))
        transcribed = sum(1 for f in files if f.get("transcript"))
        return {
            "total_videos": total_videos,
            "total_duration": total_duration,
            "average_fps": avg_fps,
            "resolutions": resolutions,
            "formats": formats,
            "audio_videos": audio_videos,
            "video_only_files": video_only,
            "transcribed_videos": transcribed,
        }

    def _load_project_metrics(self, conn: sqlite3.Connection, project_info_id: int) -> Dict[str, Any]:
        row = conn.execute(
            f"""
            SELECT total_files, total_lines, total_commits, total_contributors,
                   activity_code, activity_test, activity_doc,
                   duration_start, duration_end, duration_days,
                   doc_files, doc_words, image_files, video_files, test_files,
                   has_documentation, has_tests, has_images, has_videos,
                   languages_json, frameworks_json, skills_json
            FROM {PROJECT_INFO_TABLE}
            WHERE id = ?;
            """,
            (project_info_id,),
        ).fetchone()
        metrics = {
            "languages": [],
            "frameworks": [],
            "skills": [],
            "total_files": 0,
            "total_lines": 0,
            "total_commits": 0,
            "total_contributors": 0,
            "is_collaborative": False,
            "activity_code": 0,
            "activity_test": 0,
            "activity_doc": 0,
            "duration_start": None,
            "duration_end": None,
            "duration_days": 0,
            "doc_files": 0,
            "doc_words": 0,
            "image_files": 0,
            "video_files": 0,
            "test_files": 0,
            "has_documentation": False,
            "has_tests": False,
            "has_images": False,
            "has_videos": False,
        }
        if row:
            (
                total_files,
                total_lines,
                total_commits,
                total_contributors,
                activity_code,
                activity_test,
                activity_doc,
                duration_start,
                duration_end,
                duration_days,
                doc_files,
                doc_words,
                image_files,
                video_files,
                test_files,
                has_documentation,
                has_tests,
                has_images,
                has_videos,
                languages_json,
                frameworks_json,
                skills_json,
            ) = row
            metrics.update(
                {
                    "total_files": total_files,
                    "total_lines": total_lines,
                    "total_commits": total_commits,
                    "total_contributors": total_contributors,
                    "is_collaborative": total_contributors > 1,
                    "activity_code": activity_code,
                    "activity_test": activity_test,
                    "activity_doc": activity_doc,
                    "duration_start": duration_start,
                    "duration_end": duration_end,
                    "duration_days": duration_days,
                    "doc_files": doc_files,
                    "doc_words": doc_words,
                    "image_files": image_files,
                    "video_files": video_files,
                    "test_files": test_files,
                    "has_documentation": bool(has_documentation),
                    "has_tests": bool(has_tests),
                    "has_images": bool(has_images),
                    "has_videos": bool(has_videos),
                }
            )
            try:
                metrics["languages"] = json.loads(languages_json) if languages_json else []
            except Exception:
                metrics["languages"] = []
            try:
                metrics["frameworks"] = json.loads(frameworks_json) if frameworks_json else []
            except Exception:
                metrics["frameworks"] = []
            try:
                metrics["skills"] = json.loads(skills_json) if skills_json else []
            except Exception:
                metrics["skills"] = []
        return metrics

    def _load_presentation_items(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_name: str,
        project_metrics: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        row = conn.execute(
            f"""
            SELECT id, tagline, description, project_type, complexity, is_collaborative, summary, key_features_json
            FROM {PORTFOLIO_INSIGHTS_TABLE}
            WHERE project_info_id = ?;
            """,
            (project_info_id,),
        ).fetchone()
        if not row:
            return {}, {}
        insight_id, tagline, description, project_type, complexity, is_collaborative, summary, key_features_json = row
        try:
            features = json.loads(key_features_json) if key_features_json else []
        except Exception:
            features = []
        bullets = conn.execute(
            f"""
            SELECT bullet_text FROM {RESUME_BULLETS_TABLE}
            WHERE portfolio_insight_id = ?
            ORDER BY display_order ASC;
            """,
            (insight_id,),
        ).fetchall()
        portfolio_item = {
            "project_name": project_name,
            "tagline": tagline,
            "description": description,
            "languages": project_metrics.get("languages", []),
            "frameworks": project_metrics.get("frameworks", []),
            "skills": project_metrics.get("skills", []),
            "is_collaborative": bool(is_collaborative),
            "total_commits": project_metrics.get("total_commits", 0),
            "total_lines": project_metrics.get("total_lines", 0),
            "project_type": project_type,
            "complexity": complexity,
            "key_features": features,
            "summary": summary,
            "has_documentation": project_metrics.get("has_documentation", False),
            "has_tests": project_metrics.get("has_tests", False),
        }
        resume_item = {
            "project_name": project_name,
            "bullets": [row[0] for row in bullets],
        }
        return portfolio_item, resume_item

    def _load_git_analysis(
        self,
        conn: sqlite3.Connection,
        project_info_id: int,
        project_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        row = conn.execute(
            f"""
            SELECT contributors_json
            FROM {PROJECT_INFO_TABLE}
            WHERE id = ?;
            """,
            (project_info_id,),
        ).fetchone()
        contributor_rows: List[Dict[str, Any]] = []
        if row and row[0]:
            try:
                contributor_rows = json.loads(row[0])
            except Exception:
                contributor_rows = []
        return {
            "total_commits": project_metrics.get("total_commits", 0),
            "total_contributors": project_metrics.get("total_contributors", 0),
            "contributors": contributor_rows,
            "activity_mix": {
                "code": project_metrics.get("activity_code", 0),
                "test": project_metrics.get("activity_test", 0),
                "doc": project_metrics.get("activity_doc", 0),
            },
            "first_commit_at": project_metrics.get("duration_start"),
            "last_commit_at": project_metrics.get("duration_end"),
            "duration_days": project_metrics.get("duration_days", 0),
        }

    def _load_global_insights(self, conn: sqlite3.Connection, ingest_id: int) -> Dict[str, Any]:
        global_insights: Dict[str, Any] = {}
        ranking_row = conn.execute(
            f"""
            SELECT ranking_json
            FROM {RANKING_TABLE}
            WHERE ingest_id = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (ingest_id,),
        ).fetchone()
        if ranking_row and ranking_row[0]:
            try:
                global_insights["project_ranking"] = json.loads(ranking_row[0])
            except Exception:
                pass

        chronology_row = conn.execute(
            f"""
            SELECT chronology_json
            FROM {CHRONOLOGY_TABLE}
            WHERE ingest_id = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (ingest_id,),
        ).fetchone()
        if chronology_row and chronology_row[0]:
            try:
                global_insights["chronological_skills"] = json.loads(chronology_row[0])
            except Exception:
                pass

        return global_insights

    def _mark_backup(self) -> None:
        return


class ArtifactVideoHint:
    """Utility container for video extensions used by the orchestrator."""

    EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv"}
