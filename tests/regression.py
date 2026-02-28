import json
import uuid
import zipfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from src.api.generation import _local_resume_bullets


def _u() -> str:
    return str(uuid.uuid4())


# Issue #257 regression: ensure resume generation never returns literal "None" bullet text.
def test_local_resume_bullets_do_not_emit_literal_none():
    bullets = _local_resume_bullets(
        project_name="Archive",
        top_languages=[],
        frameworks=[],
        top_skills=[],
        user_commits=None,
        total_commits=None,
        contributor_count=None,
        collab_type=None,
        highlight_skills=None,
    )

    assert len(bullets) == 3
    assert all(str(b).strip() for b in bullets)
    assert all(str(b).strip().casefold() != "none" for b in bullets)


# Issue #258 regression: missing first_seen_ts should remain unknown (null), not upload-time fallback.
def test_portfolio_skills_chronological_keeps_unknown_timestamp_null(client, engine):
    user_id = _u()
    portfolio_id = _u()
    project_id = _u()
    snapshot_id = _u()
    analysis_id = _u()

    output_json = {
        "skills": [
            {"skill": "python", "max_prob": 0.91, "hits": 3},
        ]
    }

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, 'default')"),
            {"id": portfolio_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name) VALUES (:id, :pf, 'P')"),
            {"id": project_id, "pf": portfolio_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, ingested_at)
                VALUES (:id, :pid, 'z.zip', :zh, :ing)
                """
            ),
            {
                "id": snapshot_id,
                "pid": project_id,
                "zh": "d" * 64,
                "ing": datetime(2025, 1, 1, tzinfo=timezone.utc),
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, completed_at)
                VALUES (:id, :sid, 'local_ml', 'complete', CAST(:out AS jsonb), :completed)
                """
            ),
            {
                "id": analysis_id,
                "sid": snapshot_id,
                "out": json.dumps(output_json),
                "completed": datetime(2025, 1, 2, tzinfo=timezone.utc),
            },
        )

    r = client.get(f"/portfolio/{portfolio_id}/skills/chronological?direction=asc&limit=10")
    assert r.status_code == 200
    events = r.json()["skill_events"]
    assert len(events) == 1
    assert events[0]["skill"] == "python"
    assert events[0]["first_seen_ts"] is None


# Issue #258 regression: timeline should still render from analysis_skills when output_json.skills is absent.
def test_portfolio_skills_chronological_falls_back_to_analysis_skills(client, engine):
    user_id = _u()
    portfolio_id = _u()
    project_id = _u()
    snapshot_id = _u()
    analysis_id = _u()

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, 'default')"),
            {"id": portfolio_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name) VALUES (:id, :pf, 'P')"),
            {"id": project_id, "pf": portfolio_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256)
                VALUES (:id, :pid, 'z.zip', :zh)
                """
            ),
            {"id": snapshot_id, "pid": project_id, "zh": "d" * 64},
        )
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, completed_at)
                VALUES (:id, :sid, 'local_ml', 'complete', CAST(:out AS jsonb), NOW())
                """
            ),
            {"id": analysis_id, "sid": snapshot_id, "out": json.dumps({"totals": {"skills_detected": 1}})},
        )

        skill_id = conn.execute(
            text(
                """
                INSERT INTO skills (skill_name, category)
                VALUES ('python', 'language')
                RETURNING id
                """
            )
        ).scalar_one()

        conn.execute(
            text(
                """
                INSERT INTO analysis_skills (analysis_id, skill_id, confidence, evidence_json)
                VALUES (:aid, :sid, :conf, CAST(:ev AS jsonb))
                """
            ),
            {
                "aid": analysis_id,
                "sid": skill_id,
                "conf": 0.88,
                "ev": json.dumps(
                    {
                        "hits": 7,
                        "max_prob": 0.88,
                        "examples": [{"path": "main.py", "p": 0.88, "ts": "2023-02-03T00:00:00+00:00"}],
                    }
                ),
            },
        )

    r = client.get(f"/portfolio/{portfolio_id}/skills/chronological?direction=asc&limit=10")
    assert r.status_code == 200
    events = r.json()["skill_events"]
    assert len(events) == 1
    assert events[0]["skill"] == "python"
    assert events[0]["first_seen_ts"] == "2023-02-03T00:00:00+00:00"
    assert events[0]["max_prob"] == pytest.approx(0.88, rel=1e-6)
    assert events[0]["hits"] == 7


# Issue #258 regression: ensure ingestion preserves file timestamps used for chronology.
def test_upload_persists_snapshot_file_last_modified_timestamp(client, engine, monkeypatch, tmp_path):
    blobstore = tmp_path / "blobstore"
    blobstore.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(blobstore))

    consent = client.post(
        "/privacy-consent",
        json={"user_id": None, "consent_type": "data_access", "granted": True, "version": 1},
    )
    assert consent.status_code == 200
    user_id = consent.json()["user_id"]

    zip_path = tmp_path / "project.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        info = zipfile.ZipInfo("project/main.py")
        info.date_time = (2021, 5, 4, 3, 2, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, "print('hello')\n")

    with open(zip_path, "rb") as fp:
        upload = client.post(
            "/projects/upload",
            data={"project_name": "timestamp-test", "user_id": user_id},
            files={"file": ("project.zip", fp, "application/zip")},
        )
    assert upload.status_code == 200

    created = upload.json().get("created", [])
    assert created, "Expected uploaded project snapshot to be created"
    snapshot_id = created[0]["snapshot_id"]

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT last_modified_ts FROM snapshot_files WHERE snapshot_id = :sid"),
            {"sid": snapshot_id},
        ).scalars().all()

    assert rows, "Expected snapshot_files rows for uploaded snapshot"
    assert all(ts is not None for ts in rows)
