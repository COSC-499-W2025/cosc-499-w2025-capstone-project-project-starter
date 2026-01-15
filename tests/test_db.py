from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from src.db.base import fetch_snapshot_files
from src.db.consents import (
    is_data_access_allowed,
    is_external_services_allowed,
    snapshot_external_services_allowed,
)
from src.db.deletion import (
    delete_portfolio_showcase_and_gc,
    delete_snapshot_and_gc,
)
from src.db.user_config import (
    DEFAULT_CONFIG,
    clear_project_user_contributor_mapping,
    get_user_config,
    merge_user_config,
    put_user_config,
    set_project_user_contributor_mapping,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _mk_minimal_graph(conn):
    """
    Create: users -> portfolios -> projects -> snapshots.
    Returns (user_id, portfolio_id, project_id, snapshot_id).
    """
    user_id = _uid()
    portfolio_id = _uid()
    project_id = _uid()
    snapshot_id = _uid()

    conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
    conn.execute(
        text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, :name)"),
        {"id": portfolio_id, "uid": user_id, "name": "p0"},
    )
    conn.execute(
        text(
            """
            INSERT INTO projects (id, portfolio_id, name, project_type, collaboration_type)
            VALUES (:id, :pid, :name, 'code', 'individual')
            """
        ),
        {"id": project_id, "pid": portfolio_id, "name": "proj"},
    )
    conn.execute(
        text(
            """
            INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label)
            VALUES (:id, :prj, :zn, :zh, :lbl)
            """
        ),
        {
            "id": snapshot_id,
            "prj": project_id,
            "zn": "test.zip",
            "zh": "a" * 64,
            "lbl": "s0",
        },
    )
    return user_id, portfolio_id, project_id, snapshot_id


def test_fetch_snapshot_files_orders_and_joins(engine):
    with engine.begin() as conn:
        user_id, portfolio_id, project_id, snapshot_id = _mk_minimal_graph(conn)

        # Two blobs
        sha_a = "b" * 64
        sha_b = "c" * 64
        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, :sz, :mt, :sp)
                """
            ),
            {"sha": sha_a, "sz": 10, "mt": "text/plain", "sp": "/tmp/blob_a"},
        )
        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, :sz, :mt, :sp)
                """
            ),
            {"sha": sha_b, "sz": 20, "mt": "text/plain", "sp": "/tmp/blob_b"},
        )

        # Insert snapshot_files out of order by relative_path
        ts = datetime(2020, 1, 1, tzinfo=timezone.utc)
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files
                  (snapshot_id, relative_path, file_sha256, last_modified_ts, file_mode, size_bytes)
                VALUES
                  (:sid, :rp, :sha, :ts, :mode, :sz)
                """
            ),
            {"sid": snapshot_id, "rp": "b.txt", "sha": sha_b, "ts": ts, "mode": 0o644, "sz": 20},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files
                  (snapshot_id, relative_path, file_sha256, last_modified_ts, file_mode, size_bytes)
                VALUES
                  (:sid, :rp, :sha, :ts, :mode, :sz)
                """
            ),
            {"sid": snapshot_id, "rp": "a.txt", "sha": sha_a, "ts": ts, "mode": 0o644, "sz": 10},
        )

    rows = fetch_snapshot_files(engine, str(snapshot_id))
    assert [r.relative_path for r in rows] == ["a.txt", "b.txt"]
    assert rows[0].file_sha256 == sha_a
    assert rows[0].stored_path == "/tmp/blob_a"
    assert rows[0].size_bytes == 10
    assert rows[0].last_modified_ts is not None


def test_consents_snapshot_external_services_allowed_latest_wins(engine):
    with engine.begin() as conn:
        user_id, portfolio_id, project_id, snapshot_id = _mk_minimal_graph(conn)

        # No consent records => not allowed.
        assert snapshot_external_services_allowed(engine, str(snapshot_id)) is False

        # Insert a denied consent, then a granted consent; latest should win.
        conn.execute(
            text(
                """
                INSERT INTO privacy_consents (id, user_id, consent_type, granted, created_at)
                VALUES (:id, :uid, 'external_services', FALSE, NOW() - INTERVAL '10 minutes')
                """
            ),
            {"id": _uid(), "uid": user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO privacy_consents (id, user_id, consent_type, granted, created_at)
                VALUES (:id, :uid, 'external_services', TRUE, NOW())
                """
            ),
            {"id": _uid(), "uid": user_id},
        )

        # Direct check
        assert is_external_services_allowed(conn, str(user_id)) is True

    # Snapshot-level check (resolves owner via join snapshots->projects->portfolios->users)
    assert snapshot_external_services_allowed(engine, str(snapshot_id)) is True


def test_consents_data_access_allowed(engine):
    with engine.begin() as conn:
        user_id, _, _, _ = _mk_minimal_graph(conn)

        assert is_data_access_allowed(conn, str(user_id)) is False

        conn.execute(
            text(
                """
                INSERT INTO privacy_consents (id, user_id, consent_type, granted, created_at)
                VALUES (:id, :uid, 'data_access', TRUE, NOW())
                """
            ),
            {"id": _uid(), "uid": user_id},
        )

        assert is_data_access_allowed(conn, str(user_id)) is True


def test_user_config_default_shape_and_normalization(engine):
    with engine.begin() as conn:
        user_id, _, _, _ = _mk_minimal_graph(conn)

        cfg = get_user_config(conn, str(user_id))
        # Keys exist
        assert "identity" in cfg
        assert "ranking" in cfg
        assert "match_emails" in cfg["identity"]
        assert "match_names" in cfg["identity"]
        assert "project_contributor_map" in cfg["identity"]

        # Types are normalized
        assert isinstance(cfg["identity"]["match_emails"], list)
        assert isinstance(cfg["identity"]["match_names"], list)
        assert isinstance(cfg["identity"]["project_contributor_map"], dict)

        # put_user_config enforces normalization when given wrong types
        bad = {
            "identity": {
                "match_emails": "not-a-list",
                "match_names": None,
                "project_contributor_map": "also-not-a-dict",
            },
            "ranking": "not-a-dict",
        }
        out = put_user_config(conn, str(user_id), bad)
        assert out["identity"]["match_emails"] == []
        assert out["identity"]["match_names"] == []
        assert out["identity"]["project_contributor_map"] == {}
        assert isinstance(out["ranking"], dict)


def test_user_config_merge_and_project_contributor_mapping(engine):
    with engine.begin() as conn:
        user_id, _, project_id, _ = _mk_minimal_graph(conn)
        contributor_id = _uid()

        # Start with defaults
        cfg0 = get_user_config(conn, str(user_id))
        assert cfg0["identity"]["project_contributor_map"] == {}

        # Merge a patch
        merged = merge_user_config(conn, str(user_id), {"identity": {"match_emails": ["me@example.com"]}})
        assert merged["identity"]["match_emails"] == ["me@example.com"]

        # Set mapping
        cfg1 = set_project_user_contributor_mapping(conn, str(user_id), str(project_id), str(contributor_id))
        assert cfg1["identity"]["project_contributor_map"][str(project_id)] == str(contributor_id)

        # Clear mapping
        cfg2 = clear_project_user_contributor_mapping(conn, str(user_id), str(project_id))
        assert str(project_id) not in cfg2["identity"]["project_contributor_map"]


def test_delete_snapshot_gc_shared_blob_safety(engine):
    """
    Validates the core safety invariant:
      - If a blob is still referenced by any snapshot_files row, it must not be deleted.
      - Once it is unreferenced (and not used as a showcase thumbnail), it can be GC'd.
    """
    # Create a real temp file to safely verify filesystem deletion.
    fd, temp_path = tempfile.mkstemp(prefix="artifactminer_test_blob_", suffix=".bin")
    os.close(fd)
    with open(temp_path, "wb") as f:
        f.write(b"hello")

    shared_sha = "d" * 64

    with engine.begin() as conn:
        # Graph A
        user_a, portfolio_a, project_a, snapshot_a = _mk_minimal_graph(conn)
        # Graph B (separate snapshot, same blob)
        user_b, portfolio_b, project_b, snapshot_b = _mk_minimal_graph(conn)

        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, :sz, :mt, :sp)
                """
            ),
            {"sha": shared_sha, "sz": 5, "mt": "application/octet-stream", "sp": temp_path},
        )

        # Both snapshots reference the same blob
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files (snapshot_id, relative_path, file_sha256, size_bytes)
                VALUES (:sid, 'a.bin', :sha, 5)
                """
            ),
            {"sid": snapshot_a, "sha": shared_sha},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files (snapshot_id, relative_path, file_sha256, size_bytes)
                VALUES (:sid, 'b.bin', :sha, 5)
                """
            ),
            {"sid": snapshot_b, "sha": shared_sha},
        )

    # Delete snapshot A: blob must remain (still referenced by snapshot B)
    out1 = delete_snapshot_and_gc(engine, str(snapshot_a))
    assert out1["deleted"] is True

    with engine.connect() as conn:
        still_there = conn.execute(
            text("SELECT 1 FROM file_blobs WHERE sha256 = :sha"),
            {"sha": shared_sha},
        ).scalar()
        assert still_there == 1
    assert os.path.exists(temp_path) is True

    # Delete snapshot B: blob now unreferenced; should be GC'd
    out2 = delete_snapshot_and_gc(engine, str(snapshot_b))
    assert out2["deleted"] is True

    with engine.connect() as conn:
        gone = conn.execute(
            text("SELECT 1 FROM file_blobs WHERE sha256 = :sha"),
            {"sha": shared_sha},
        ).scalar()
        assert gone is None

    # Best-effort filesystem cleanup should remove the temp file.
    assert os.path.exists(temp_path) is False


def test_delete_portfolio_showcase_gc_keeps_blob_until_showcase_deleted(engine):
    """
    Validates that GC does not delete blobs referenced by portfolio_showcases.thumbnail_blob_sha256,
    even if snapshots are deleted. Then deleting the showcase allows GC.
    """
    fd, temp_path = tempfile.mkstemp(prefix="artifactminer_test_thumb_", suffix=".png")
    os.close(fd)
    with open(temp_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nfake")

    sha = "e" * 64

    with engine.begin() as conn:
        user_id, portfolio_id, project_id, snapshot_id = _mk_minimal_graph(conn)
        showcase_id = _uid()

        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, :sz, :mt, :sp)
                """
            ),
            {"sha": sha, "sz": 12, "mt": "image/png", "sp": temp_path},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files (snapshot_id, relative_path, file_sha256, size_bytes)
                VALUES (:sid, 'thumb.png', :sha, 12)
                """
            ),
            {"sid": snapshot_id, "sha": sha},
        )
        conn.execute(
            text(
                """
                INSERT INTO portfolio_showcases (id, project_id, thumbnail_blob_sha256, content_json)
                VALUES (:id, :pid, :sha, '{}'::jsonb)
                """
            ),
            {"id": showcase_id, "pid": project_id, "sha": sha},
        )

    # Delete snapshot: blob must remain due to showcase thumbnail reference.
    delete_snapshot_and_gc(engine, str(snapshot_id))
    with engine.connect() as conn:
        still_there = conn.execute(text("SELECT 1 FROM file_blobs WHERE sha256 = :sha"), {"sha": sha}).scalar()
        assert still_there == 1
    assert os.path.exists(temp_path) is True

    # Delete showcase: now blob is unreferenced and should GC.
    out = delete_portfolio_showcase_and_gc(engine, str(showcase_id))
    assert out["deleted"] is True

    with engine.connect() as conn:
        gone = conn.execute(text("SELECT 1 FROM file_blobs WHERE sha256 = :sha"), {"sha": sha}).scalar()
        assert gone is None
    assert os.path.exists(temp_path) is False
