import uuid
from datetime import datetime, timezone
import io
import tempfile
import shutil
import zipfile
import os
from pypdf import PdfReader

from sqlalchemy import text
import re
import json
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

from PIL import Image

import tempfile
from pathlib import Path

from io import BytesIO
import base64
from reportlab.lib.pagesizes import LETTER
from src.api.pdf_exporter import export_portfolio_top_projects_pdf,export_resume_item_pdf_bytes

from git import Repo, InvalidGitRepositoryError

from src.api.ingest import extract_commits_from_git_zip, extract_commit_counts_from_git_zip



def _u() -> str:
    return str(uuid.uuid4())

def _mk_graph(engine):
    """
    Creates: users -> portfolios -> projects -> snapshots.
    Returns (user_id, portfolio_id, project_id, snapshot_id).
    """
    user_id = _u()
    portfolio_id = _u()
    project_id = _u()
    snapshot_id = _u()

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
                INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label)
                VALUES (:id, :pid, 'z.zip', :zh, 'S')
                """
            ),
            {"id": snapshot_id, "pid": project_id, "zh": "d" * 64},
        )

    return user_id, portfolio_id, project_id, snapshot_id

# def fake_thumbnail_blob():
#     # 1x1 PNG transparent pixel
#     png_base64 = (
#         "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
#         "/w8AAgMBAQEGxEAAAAAASUVORK5CYII="
#     )
#     return {
#         "data_base64": png_base64,
#         "mime_type": "image/png"
#     }



def test_privacy_consent_creates_user_and_config(client):
    r = client.post(
        "/privacy-consent",
        json={"consent_type": "data_access", "granted": True, "version": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert "user_id" in body
    user_id = body["user_id"]

    r2 = client.get(f"/users/{user_id}/config")
    assert r2.status_code == 200
    assert r2.json()["user_id"] == user_id
    assert isinstance(r2.json()["config"], dict)


def test_upload_rejects_non_zip(client):
    # Endpoint requires filename ending with .zip
    files = {"file": ("not-a-zip.txt", b"hello", "text/plain")}
    r = client.post("/projects/upload", files=files, data={})
    assert r.status_code == 400
    assert "Expected a .zip upload" in r.text


def test_delete_snapshot_does_not_gc_shared_file_blob(client, engine):
    # Create user/portfolio/project + two snapshots sharing one blob.
    user_id = _u()
    portfolio_id = _u()
    project_id = _u()
    snapshot_a = _u()
    snapshot_b = _u()

    sha_shared = "a" * 64

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, 'default')"),
            {"id": portfolio_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name) VALUES (:id, :pf, 'P1')"),
            {"id": project_id, "pf": portfolio_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label)
                VALUES (:id, :pid, 'x.zip', :zh, 'A')
                """
            ),
            {"id": snapshot_a, "pid": project_id, "zh": "b" * 64},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label)
                VALUES (:id, :pid, 'y.zip', :zh, 'B')
                """
            ),
            {"id": snapshot_b, "pid": project_id, "zh": "c" * 64},
        )

        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, 3, 'text/plain', '/tmp/does-not-matter')
                """
            ),
            {"sha": sha_shared},
        )

        conn.execute(
            text(
                """
                INSERT INTO snapshot_files (snapshot_id, relative_path, file_sha256, size_bytes)
                VALUES (:sid, :rp, :sha, 3)
                """
            ),
            {"sid": snapshot_a, "rp": "a.txt", "sha": sha_shared},
        )
        conn.execute(
            text(
                """
                INSERT INTO snapshot_files (snapshot_id, relative_path, file_sha256, size_bytes)
                VALUES (:sid, :rp, :sha, 3)
                """
            ),
            {"sid": snapshot_b, "rp": "b.txt", "sha": sha_shared},
        )

    # Delete snapshot A; shared blob must remain because snapshot B still references it.
    r = client.delete(f"/snapshots/{snapshot_a}")
    assert r.status_code == 200

    with engine.connect() as conn:
        still_there = conn.execute(
            text("SELECT 1 FROM file_blobs WHERE sha256 = :sha"),
            {"sha": sha_shared},
        ).scalar()
        assert still_there == 1

        b_ref = conn.execute(
            text("SELECT 1 FROM snapshot_files WHERE snapshot_id = :sid AND file_sha256 = :sha"),
            {"sid": snapshot_b, "sha": sha_shared},
        ).scalar()
        assert b_ref == 1

        a_exists = conn.execute(
            text("SELECT 1 FROM snapshots WHERE id = :sid"),
            {"sid": snapshot_a},
        ).scalar()
        assert a_exists is None


def test_portfolio_projects_chronological_endpoint(client, engine):
    user_id = _u()
    portfolio_id = _u()

    t1 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2021, 1, 1, tzinfo=timezone.utc)
    t3 = datetime(2022, 1, 1, tzinfo=timezone.utc)

    p1 = _u()
    p2 = _u()
    p3 = _u()

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, 'default')"),
            {"id": portfolio_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name, created_at) VALUES (:id, :pf, 'A', :ts)"),
            {"id": p1, "pf": portfolio_id, "ts": t2},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name, created_at) VALUES (:id, :pf, 'B', :ts)"),
            {"id": p2, "pf": portfolio_id, "ts": t1},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name, created_at) VALUES (:id, :pf, 'C', :ts)"),
            {"id": p3, "pf": portfolio_id, "ts": t3},
        )

    r = client.get(f"/portfolio/{portfolio_id}/projects/chronological?direction=asc&limit=10")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["projects"]]
    assert ids == [p2, p1, p3]


def test_portfolio_skills_chronological_endpoint(client, engine):
    user_id = _u()
    portfolio_id = _u()
    project_id = _u()
    snapshot_id = _u()
    analysis_id = _u()

    # Two skill events with explicit first_seen_ts ordering.
    output_json = {
        "skills": [
            {"skill": "python", "first_seen_ts": "2020-01-01T00:00:00+00:00", "max_prob": 0.9, "hits": 10},
            {"skill": "fastapi", "first_seen_ts": "2021-01-01T00:00:00+00:00", "max_prob": 0.8, "hits": 5},
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
            {"id": analysis_id, "sid": snapshot_id, "out": json.dumps(output_json)},
        )

    r = client.get(f"/portfolio/{portfolio_id}/skills/chronological?direction=asc&limit=10")
    assert r.status_code == 200
    events = r.json()["skill_events"]
    assert [e["skill"] for e in events[:2]] == ["python", "fastapi"]

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_users_config_put_and_patch(client, engine):
    user_id, _, _, _ = _mk_graph(engine)

    r_put = client.put(f"/users/{user_id}/config", json={"config": {"identity": {"match_emails": ["me@example.com"]}}})
    assert r_put.status_code == 200
    body_put = r_put.json()
    assert body_put["user_id"] == user_id
    assert body_put["config"]["identity"]["match_emails"] == ["me@example.com"]

    r_patch = client.patch(f"/users/{user_id}/config", json={"identity": {"match_names": ["Me"]}})
    assert r_patch.status_code == 200
    body_patch = r_patch.json()
    assert body_patch["config"]["identity"]["match_emails"] == ["me@example.com"]
    assert body_patch["config"]["identity"]["match_names"] == ["Me"]


def test_list_projects_requires_scope(client):
    r = client.get("/projects")
    assert r.status_code == 400
    assert "Provide portfolio_id or user_id" in r.text


def test_list_projects_by_portfolio_and_user_default_portfolio(client, engine):
    user_id, portfolio_id, project_id, snapshot_id = _mk_graph(engine)

    # By portfolio_id
    r1 = client.get(f"/projects?portfolio_id={portfolio_id}")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["portfolio_id"] == portfolio_id
    assert [p["id"] for p in body1["projects"]] == [project_id]

    # By user_id (uses default portfolio if exists)
    r2 = client.get(f"/projects?user_id={user_id}")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["portfolio_id"] == portfolio_id
    assert [p["id"] for p in body2["projects"]] == [project_id]
    assert body2["projects"][0]["latest_snapshot"]["id"] == snapshot_id


def test_get_portfolio_404_and_ok(client, engine):
    r0 = client.get(f"/portfolio/{_u()}")
    assert r0.status_code == 404

    user_id, portfolio_id, _, _ = _mk_graph(engine)
    r = client.get(f"/portfolio/{portfolio_id}")
    assert r.status_code == 200
    body = r.json()
    assert str(body["id"]) == portfolio_id
    assert str(body["user_id"]) == user_id
    assert body["name"] == "default"


def test_snapshot_analyses_list_order_and_fields(client, engine):
    _, _, _, snapshot_id = _mk_graph(engine)

    a1 = _u()
    a2 = _u()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, started_at)
                VALUES (:id, :sid, 'parser', 'complete', '{}'::jsonb, NOW() - INTERVAL '5 minutes')
                """
            ),
            {"id": a1, "sid": snapshot_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, started_at)
                VALUES (:id, :sid, 'local_ml', 'pending', '{"error":"x"}'::jsonb, NOW() - INTERVAL '1 minutes')
                """
            ),
            {"id": a2, "sid": snapshot_id},
        )

    r = client.get(f"/snapshots/{snapshot_id}/analyses")
    assert r.status_code == 200
    body = r.json()
    assert body["snapshot_id"] == snapshot_id
    assert len(body["analyses"]) == 2
    assert body["analyses"][0]["analysis_type"] == "parser"
    assert body["analyses"][1]["analysis_type"] == "local_ml"
    # error is projected from output_json->>'error'
    assert body["analyses"][0]["error"] is None
    assert body["analyses"][1]["error"] == "x"


def test_snapshot_skills_endpoint_uses_analysis_skills(client, engine):
    _, _, _, snapshot_id = _mk_graph(engine)
    analysis_id = _u()

    # Create 2 skills and link to analysis_skills.
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, completed_at)
                VALUES (:id, :sid, 'local_ml', 'complete', '{}'::jsonb, NOW())
                """
            ),
            {"id": analysis_id, "sid": snapshot_id},
        )
        conn.execute(
            text("INSERT INTO skills (skill_name, category) VALUES ('python', 'language'), ('fastapi', 'framework')"),
        )
        py_id = conn.execute(text("SELECT id FROM skills WHERE skill_name='python'")).scalar_one()
        fa_id = conn.execute(text("SELECT id FROM skills WHERE skill_name='fastapi'")).scalar_one()

        conn.execute(
            text(
                """
                INSERT INTO analysis_skills (analysis_id, skill_id, confidence)
                VALUES (:aid, :sid, 0.9), (:aid, :sid2, 0.8)
                """
            ),
            {"aid": analysis_id, "sid": py_id, "sid2": fa_id},
        )

    r = client.get(f"/snapshots/{snapshot_id}/skills?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["snapshot_id"] == snapshot_id
    assert body["analysis_id"] == analysis_id
    assert [s["skill_name"] for s in body["skills"][:2]] == ["python", "fastapi"]


def test_external_analysis_falls_back_to_local_ml_without_consent(client, engine):
    user_id, _, _, snapshot_id = _mk_graph(engine)

    # No external_services consent => POST returns local_ml pending (created if missing).
    r = client.post(f"/snapshots/{snapshot_id}/external-analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["external_allowed"] is False
    assert body["used"] == "local_ml"
    assert body["status"] == "pending"
    assert "analysis_id" in body

    # GET should also return local_ml latest.
    r2 = client.get(f"/snapshots/{snapshot_id}/external-analysis")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["external_allowed"] is False
    assert body2["analysis"] is not None
    assert body2["analysis"]["status"] == "pending"


def test_external_analysis_uses_external_llm_with_consent(client, engine):
    user_id, _, _, snapshot_id = _mk_graph(engine)

    # Grant external_services consent
    client.post("/privacy-consent", json={"user_id": user_id, "consent_type": "external_services", "granted": True, "version": 1})

    r = client.post(f"/snapshots/{snapshot_id}/external-analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["external_allowed"] is True
    assert body["used"] == "external_llm"
    assert body["status"] == "pending"

    r2 = client.get(f"/snapshots/{snapshot_id}/external-analysis")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["external_allowed"] is True
    assert body2["analysis"] is not None
    assert body2["analysis"]["status"] == "pending"


def test_project_contributors_list_and_set_user(client, engine):
    user_id, _, project_id, snapshot_id = _mk_graph(engine)

    # 404 branch
    r0 = client.get(f"/projects/{_u()}/contributors")
    assert r0.status_code == 404

    cid1 = _u()
    cid2 = _u()

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO contributors (id, canonical_name, email) VALUES (:id, 'Me', 'me@example.com')"),
            {"id": cid1},
        )
        conn.execute(
            text("INSERT INTO contributors (id, canonical_name, email) VALUES (:id, 'Other', 'o@example.com')"),
            {"id": cid2},
        )
        conn.execute(
            text("INSERT INTO project_contributors (project_id, contributor_id, is_user) VALUES (:pid, :cid, FALSE), (:pid, :cid2, FALSE)"),
            {"pid": project_id, "cid": cid1, "cid2": cid2},
        )
        conn.execute(
            text(
                """
                INSERT INTO contribution_events (snapshot_id, contributor_id, activity_type, commit_count)
                VALUES (:sid, :c1, 'code', 10), (:sid, :c2, 'code', 5)
                """
            ),
            {"sid": snapshot_id, "c1": cid1, "c2": cid2},
        )

    r = client.get(f"/projects/{project_id}/contributors")
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == project_id
    assert len(body["contributors"]) == 2
    # Ordered by is_user desc then commits desc; initially both FALSE so commits desc.
    assert body["contributors"][0]["commits"] == 10

    # Set cid2 as user (also unsets others)
    r2 = client.post(
        f"/projects/{project_id}/contributors/{cid2}/set-user",
        json={"is_user": True, "unset_others": True, "persist_to_config": True},
    )
    assert r2.status_code == 200
    assert r2.json()["is_user"] is True

    r3 = client.get(f"/projects/{project_id}/contributors")
    assert r3.status_code == 200
    out = r3.json()["contributors"]
    assert out[0]["contributor_id"] == cid2
    assert out[0]["is_user"] is True


def test_refresh_project_collaboration(client, engine):
    _, _, project_id, _ = _mk_graph(engine)

    cid1 = _u()
    cid2 = _u()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO contributors (id, canonical_name) VALUES (:id, 'A'), (:id2, 'B')"), {"id": cid1, "id2": cid2})
        conn.execute(text("INSERT INTO project_contributors (project_id, contributor_id) VALUES (:pid, :cid)"), {"pid": project_id, "cid": cid1})

    r1 = client.post(f"/projects/{project_id}/refresh-collaboration")
    assert r1.status_code == 200
    assert r1.json()["collaboration_type"] == "individual"
    assert r1.json()["contributor_count"] == 1

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO project_contributors (project_id, contributor_id) VALUES (:pid, :cid)"), {"pid": project_id, "cid": cid2})

    r2 = client.post(f"/projects/{project_id}/refresh-collaboration")
    assert r2.status_code == 200
    assert r2.json()["collaboration_type"] == "collaborative"
    assert r2.json()["contributor_count"] == 2


def test_identity_rules_and_auto_link_dry_run(client, engine):
    user_id, portfolio_id, project_id, snapshot_id = _mk_graph(engine)

    # Create contributors + contributions
    cid_me = _u()
    cid_other = _u()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO contributors (id, canonical_name, email) VALUES (:id, 'Me', 'me@example.com')"),
            {"id": cid_me},
        )
        conn.execute(
            text("INSERT INTO contributors (id, canonical_name, email) VALUES (:id, 'Other', 'o@example.com')"),
            {"id": cid_other},
        )
        conn.execute(
            text("INSERT INTO project_contributors (project_id, contributor_id, is_user) VALUES (:pid, :c1, FALSE), (:pid, :c2, FALSE)"),
            {"pid": project_id, "c1": cid_me, "c2": cid_other},
        )
        conn.execute(
            text(
                """
                INSERT INTO contribution_events (snapshot_id, contributor_id, activity_type, commit_count)
                VALUES (:sid, :c1, 'code', 7), (:sid, :c2, 'code', 2)
                """
            ),
            {"sid": snapshot_id, "c1": cid_me, "c2": cid_other},
        )

    # Write identity rules
    r_rules = client.post(f"/users/{user_id}/identity/rules", json={"match_emails": ["me@example.com"], "match_names": []})
    assert r_rules.status_code == 200
    assert r_rules.json()["user_id"] == user_id

    # Dry-run auto-link should choose cid_me, but not apply.
    r_auto = client.post(f"/users/{user_id}/identity/auto-link", json={"portfolio_id": portfolio_id, "dry_run": True, "persist_project_map": True})
    assert r_auto.status_code == 200
    body = r_auto.json()
    assert body["user_id"] == user_id
    assert body["dry_run"] is True
    assert len(body["results"]) == 1
    assert body["results"][0]["project_id"] == project_id
    assert body["results"][0]["chosen_contributor_id"] == cid_me
    assert body["results"][0]["applied"] is False

    # Ensure DB not updated (still no is_user TRUE)
    with engine.connect() as conn:
        n_user = conn.execute(
            text("SELECT COUNT(*) FROM project_contributors WHERE project_id = :pid AND is_user = TRUE"),
            {"pid": project_id},
        ).scalar_one()
        assert int(n_user) == 0


def test_generated_portfolio_artifacts_list_and_delete_showcase(client, engine):
    user_id, portfolio_id, project_id, _ = _mk_graph(engine)

    showcase_id = _u()
    blob_sha = "f" * 64

    with engine.begin() as conn:
        # blob referenced by showcase thumbnail
        conn.execute(
            text(
                """
                INSERT INTO file_blobs (sha256, size_bytes, mime_type, stored_path)
                VALUES (:sha, 1, 'image/png', '/tmp/does-not-matter')
                """
            ),
            {"sha": blob_sha},
        )
        conn.execute(
            text(
                """
                INSERT INTO portfolio_showcases (id, project_id, thumbnail_blob_sha256, content_json)
                VALUES (:id, :pid, :sha, '{"k":"v"}'::jsonb)
                """
            ),
            {"id": showcase_id, "pid": project_id, "sha": blob_sha},
        )

    r = client.get(f"/portfolio/{portfolio_id}/generated?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["portfolio_id"] == portfolio_id
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == showcase_id

    r_del = client.delete(f"/portfolio/showcases/{showcase_id}")
    assert r_del.status_code == 200

    # After deletion it should not appear.
    r2 = client.get(f"/portfolio/{portfolio_id}/generated?limit=10")
    assert r2.status_code == 200
    assert r2.json()["items"] == []


def test_resume_get_and_pdf_404s(client):
    rid = _u()
    r = client.get(f"/resume/{rid}")
    assert r.status_code == 404
    r2 = client.get(f"/resume/{rid}/pdf")
    assert r2.status_code == 404


def test_delete_resume_and_analysis_endpoints(client, engine):
    _, _, project_id, snapshot_id = _mk_graph(engine)

    resume_id = _u()
    analysis_id = _u()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO resume_items (id, project_id, content_json)
                VALUES (:id, :pid, '{"title":"x"}'::jsonb)
                """
            ),
            {"id": resume_id, "pid": project_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json)
                VALUES (:id, :sid, 'local_ml', 'complete', '{}'::jsonb)
                """
            ),
            {"id": analysis_id, "sid": snapshot_id},
        )

    r1 = client.delete(f"/resume/{resume_id}")
    assert r1.status_code == 200
    r2 = client.delete(f"/analyses/{analysis_id}")
    assert r2.status_code == 200

    # Delete 404s
    r3 = client.delete(f"/resume/{resume_id}")
    assert r3.status_code == 404
    r4 = client.delete(f"/analyses/{analysis_id}")
    assert r4.status_code == 404

# --- Helper to create a dummy zip file in memory ---
def _create_dummy_zip():
    s = io.BytesIO()
    with zipfile.ZipFile(s, 'w') as z:
        z.writestr('main.py', 'print("Hello World")')
    s.seek(0)
    return s

def test_project_display_name_update_and_resume_integration(client, monkeypatch, tmp_path):
    """
    1. Upload a project (defaults to filename).
    2. PATCH the display_name.
    3. Generate resume and verify it uses the new display_name.
    """
    
    # Set the environment variable
    test_blob_dir = tmp_path / "test_blobs"
    test_blob_dir.mkdir()
    
    # matches the key found in app.py
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(test_blob_dir))
    
    # Create a user and grant consent
    r_consent = client.post(
        "/privacy-consent",
        json={"consent_type": "data_access", "granted": True, "version": 1},
    )
    assert r_consent.status_code == 200
    user_id = r_consent.json()["user_id"]

    # Upload a project w fake zip helper func
    zip_buf = _create_dummy_zip()
    r_upload = client.post(
        "/projects/upload",
        files={"file": ("ugly_filename_v1.zip", zip_buf, "application/zip")},
        data={"user_id": user_id}
    )
    assert r_upload.status_code == 200
    
    # Get the ID and confirm initial name is the filename
    project_data = r_upload.json()["created"][0]
    project_id = project_data["project_id"]
    assert project_data["project_name"] == "ugly_filename_v1.zip"

    # UPDATE (Patch) the Display Name
    new_name = "My Polished Project"
    r_patch = client.patch(
        f"/projects/{project_id}",
        json={"display_name": new_name}
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["display_name"] == new_name

    # Generate Resume - verifies the SQL query uses COALESCE(display_name, name)
    r_resume = client.post(
        "/resume/generate",
        json={"project_id": project_id, "prefer_external_bullets": False}
    )
    assert r_resume.status_code == 200
    
    # Verify the PDF content data
    content = r_resume.json()["content"]
    assert content["project"]["name"] == new_name
    assert content["project"]["name"] != "ugly_filename_v1.zip"




def test_export_portfolio_pdf_with_image(tmp_path):
    """Test PDF generation with top projects including a valid portfolio image."""
    
    # Create a dummy image file
    img_file = tmp_path / "dummy.png"
    img = Image.new("RGB", (10, 10), color="red")  # 10x10 red square
    img.save(img_file)

    projects = [
        {
            "project_name": "Project Alpha",
            "summary_text": "Summary text here.",
            "resume_bullets": ["Bullet 1", "Bullet 2"],
            "portfolio_image": str(img_file)
        },
        {
            "project_name": "Project Beta",
            "summary_text": "Another summary",
            "resume_bullets": ["Bullet 3"],
            "portfolio_image": "nonexistent.png"  # invalid path
        }
    ]

    portfolio_data = {
        "portfolio_id": "test_portfolio",
        "generated_at": "2026-01-18",
        "top_projects": projects
    }

    pdf_file = tmp_path / "portfolio_with_images.pdf"
    result = export_portfolio_top_projects_pdf(portfolio_data, filename=str(pdf_file))

    assert pdf_file.exists()


def test_export_portfolio_pdf_empty(tmp_path):
    """Test PDF generation with no projects (empty portfolio)."""
    portfolio_data = {
        "portfolio_id": "empty_portfolio",
        "generated_at": "2026-01-18",
        "top_projects": []
    }
    pdf_file = tmp_path / "empty_portfolio.pdf"
    result = export_portfolio_top_projects_pdf(portfolio_data, filename=str(pdf_file))

    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0
    assert result == str(pdf_file)


def test_export_portfolio_pdf_invalid_data(tmp_path):
    """Test PDF generation with invalid input (should not crash)."""
    pdf_file = tmp_path / "invalid_portfolio.pdf"
    result = export_portfolio_top_projects_pdf("not_a_dict", filename=str(pdf_file))
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0
    assert result == str(pdf_file)


def test_set_project_image_project_not_found(client):
    response = client.put(
        "/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/image",
        files={"file": ("test.png", b"fakeimage", "image/png")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_pdf_hide_all_content(client, monkeypatch, tmp_path):
    """Verifies that setting all toggles to False results in a nearly empty PDF (Title only)."""
    # Setup environment
    test_blob_dir = tmp_path / "test_blobs_hide_all"
    test_blob_dir.mkdir()
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(test_blob_dir))
    
    # 1. User & Project Setup
    r_consent = client.post("/privacy-consent", json={"consent_type": "data_access", "granted": True, "version": 1})
    user_id = r_consent.json()["user_id"]
    
    zip_buf = _create_dummy_zip()
    r_upload = client.post("/projects/upload", files={"file": ("test.zip", zip_buf, "application/zip")}, data={"user_id": user_id})
    project_id = r_upload.json()["created"][0]["project_id"]

    # 2. Config: Set EVERYTHING to False
    client.patch(f"/users/{user_id}/config", json={
        "resume_filters": {
            "show_metadata": False,
            "show_summary": False,
            "show_bullets": False
        }
    })

    # 3. Generate & Fetch
    r_gen = client.post("/resume/generate", json={"project_id": project_id})
    resume_id = r_gen.json()["resume_id"]
    r_pdf = client.get(f"/resume/{resume_id}/pdf?user_id={user_id}")
    
    # 4. Verification
    pdf_reader = PdfReader(io.BytesIO(r_pdf.content))
    page_text = pdf_reader.pages[0].extract_text()

    # Assert that everything appears to be gone, the summary, the metadata, and the resume bullets and heading
    assert "Resume Item ID:" not in page_text
    assert "Summary" not in page_text
    assert "Resume Bullets" not in page_text
    assert "-" not in page_text 


def test_pdf_hide_summary_keep_bullets(client, monkeypatch, tmp_path):
    """Verifies that we can hide the summary but still see the bullets."""
    # Setup environment
    test_blob_dir = tmp_path / "test_blobs_summary_toggle"
    test_blob_dir.mkdir()
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(test_blob_dir))
    
    r_consent = client.post("/privacy-consent", json={"consent_type": "data_access", "granted": True, "version": 1})
    user_id = r_consent.json()["user_id"]
    
    zip_buf = _create_dummy_zip()
    r_upload = client.post("/projects/upload", files={"file": ("test.zip", zip_buf, "application/zip")}, data={"user_id": user_id})
    project_id = r_upload.json()["created"][0]["project_id"]

    # 2. Config: Hide summary, keep bullets (max 2)
    client.patch(f"/users/{user_id}/config", json={
        "resume_filters": {
            "show_summary": False,
            "show_bullets": True,
            "max_bullets": 2
        }
    })

    # 3. Generate & Fetch
    r_gen = client.post("/resume/generate", json={"project_id": project_id})
    resume_id = r_gen.json()["resume_id"]
    r_pdf = client.get(f"/resume/{resume_id}/pdf?user_id={user_id}")
    
    # 4. Verification
    pdf_reader = PdfReader(io.BytesIO(r_pdf.content))
    page_text = pdf_reader.pages[0].extract_text()

    # check that the heading and text are gone, but that the bullets (at least one) and the metadata are still there
    assert "Summary" not in page_text
    assert "-" in page_text
    assert "Resume Item ID:" in page_text

def test_pdf_metadata_and_bullet_toggles(client, monkeypatch, tmp_path):
    """Verifies that we can hide metadata and limit the number of bullets while keeping the summary."""
    # Setup environment: Create a temporary directory for file storage to avoid cluttering local space
    test_blob_dir = tmp_path / "test_blobs"
    test_blob_dir.mkdir()
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(test_blob_dir))
    
    # 1. User & Consent: Create a user and grant privacy consent so the API allows data processing
    r_consent = client.post("/privacy-consent", json={"consent_type": "data_access", "granted": True, "version": 1})
    user_id = r_consent.json()["user_id"]

    # 2. Project Upload: Upload a dummy ZIP file to associate with the resume generation
    zip_buf = _create_dummy_zip()
    r_upload = client.post(
        "/projects/upload",
        files={"file": ("test.zip", zip_buf, "application/zip")},
        data={"user_id": user_id}
    )
    project_id = r_upload.json()["created"][0]["project_id"]

    # 3. Config: Set filters to hide metadata and limit bullets to exactly 1
    client.patch(f"/users/{user_id}/config", json={
        "resume_filters": {"show_metadata": False, "max_bullets": 1}
    })

    # 4. Generate: Trigger the AI/Logic to create the resume content in the database
    r_gen = client.post("/resume/generate", json={"project_id": project_id})
    assert r_gen.status_code == 200
    resume_id = r_gen.json()["resume_id"]

    # 5. Export: Retrieve the generated PDF using the user's specific filter settings
    r_pdf = client.get(f"/resume/{resume_id}/pdf?user_id={user_id}")
    assert r_pdf.status_code == 200

    # 6. Verification: Extract text from the PDF and verify the toggles were respected
    pdf_reader = PdfReader(io.BytesIO(r_pdf.content))
    page_text = pdf_reader.pages[0].extract_text()
    
    # Count occurrences of the hyphen character used for bullets
    bullet_count = page_text.count("-") 
    
    # Assertions: Verify one bullet, no metadata ID, and that the Summary header is still visible
    assert bullet_count == 1, f"Expected 1 bullet, but found {bullet_count}"
    assert "Resume Item ID:" not in page_text
    assert "Summary" in page_text

def test_projects_compare_endpoint_attribute_precedence_and_highlights(client, engine):
    # Setup: one user/portfolio with two projects, each having a local_ml analysis with a python skill.
    user_id = _u()
    portfolio_id = _u()
    p1 = _u()
    p2 = _u()
    s1 = _u()
    s2 = _u()
    a1 = _u()
    a2 = _u()

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO portfolios (id, user_id, name) VALUES (:id, :uid, 'default')"),
            {"id": portfolio_id, "uid": user_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name) VALUES (:id, :pf, 'P1')"),
            {"id": p1, "pf": portfolio_id},
        )
        conn.execute(
            text("INSERT INTO projects (id, portfolio_id, name) VALUES (:id, :pf, 'P2')"),
            {"id": p2, "pf": portfolio_id},
        )
        conn.execute(
            text(
                "INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label) "
                "VALUES (:id, :pid, 'z1.zip', :zh, 'S1')"
            ),
            {"id": s1, "pid": p1, "zh": "1" * 64},
        )
        conn.execute(
            text(
                "INSERT INTO snapshots (id, project_id, source_zip_name, source_zip_sha256, snapshot_label) "
                "VALUES (:id, :pid, 'z2.zip', :zh, 'S2')"
            ),
            {"id": s2, "pid": p2, "zh": "2" * 64},
        )

        # Seed local_ml output_json with skills so build_project_report can derive skills_top.
        ml_out_1 = {
            "skills": [
                {"skill": "python", "first_seen_ts": "2020-01-01T00:00:00+00:00", "max_prob": 0.95, "hits": 10}
            ]
        }
        ml_out_2 = {
            "skills": [
                {"skill": "python", "first_seen_ts": "2020-06-01T00:00:00+00:00", "max_prob": 0.90, "hits": 8}
            ]
        }

        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, completed_at)
                VALUES (:id, :sid, 'local_ml', 'complete', CAST(:out AS jsonb), NOW())
                """
            ),
            {"id": a1, "sid": s1, "out": json.dumps(ml_out_1)},
        )
        conn.execute(
            text(
                """
                INSERT INTO analyses (id, snapshot_id, analysis_type, status, output_json, completed_at)
                VALUES (:id, :sid, 'local_ml', 'complete', CAST(:out AS jsonb), NOW())
                """
            ),
            {"id": a2, "sid": s2, "out": json.dumps(ml_out_2)},
        )

    # User config controls attribute selection when attributes= is not provided.
    r_cfg = client.patch(
        f"/users/{user_id}/config",
        json={
            "comparison": {"attributes": ["meta", "skills_top"]},
            "highlights": {"skills": ["python"]},
        },
    )
    assert r_cfg.status_code == 200

    # 1) No explicit attributes => use user_config.comparison.attributes
    r = client.get(f"/projects/compare?project_ids={p1}&project_ids={p2}")
    assert r.status_code == 200
    body = r.json()
    assert body["portfolio_id"] == portfolio_id
    assert body["project_ids"] == [p1, p2]
    assert body["attributes"] == ["meta", "skills_top"]
    assert body["highlight_skills"] == ["python"]
    assert len(body["projects"]) == 2

    for proj in body["projects"]:
        assert proj["project_id"] in (p1, p2)
        assert "meta" in proj
        assert "skills_top" in proj
        py_rows = [s for s in proj["skills_top"] if (s.get("skill") or "").casefold() == "python"]
        assert len(py_rows) >= 1
        assert py_rows[0].get("is_highlight") is True

    # 2) Explicit attributes query param overrides user_config and supports comma-separated ids.
    r2 = client.get(f"/projects/compare?project_ids={p1},{p2}&attributes=meta")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["project_ids"] == [p1, p2]
    assert body2["attributes"] == ["meta"]
    assert all(("meta" in p and "skills_top" not in p) for p in body2["projects"])
    
import os
import uuid
import tempfile

from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

TEST_DATA_DIR = "tests/data"


def test_incremental_project_upload():
    """
    Req #21:
    The system must allow incremental information by adding another
    zipped folder of files for the same project at a later point in time.
    """

    zip_v1 = os.path.join(TEST_DATA_DIR, "code_collab_proj_v1.zip")
    zip_v2 = os.path.join(TEST_DATA_DIR, "code_collab_proj_v2.zip")

    project_name = f"req21-test-{uuid.uuid4()}"

    with tempfile.TemporaryDirectory() as tmp_blobstore:
        # Point the blobstore to a temporary folder so it's writable in tests
        os.environ["ARTIFACT_MINER_BLOBSTORE"] = tmp_blobstore

        # ---- Grant privacy consent ----
        consent_response = client.post(
            "/privacy-consent",
            json={
                "user_id": None,              # Let the server create a new user
                "consent_type": "data_access",
                "granted": True,
                "version": 1
            }
        )
        assert consent_response.status_code == 200
        user_id = consent_response.json()["user_id"]

        # ---- Upload first snapshot ----
        with open(zip_v1, "rb") as f:
            response_v1 = client.post(
                "/projects/upload",
                data={
                    "project_name": project_name,
                    "user_id": user_id
                },
                files={
                    "file": ("code_collab_proj_v1.zip", f, "application/zip")
                },
            )

        assert response_v1.status_code == 200
        data_v1 = response_v1.json()
        assert "created" in data_v1
        assert len(data_v1["created"]) >= 1
        project_id = data_v1["created"][0]["project_id"]

        # ---- Upload second snapshot (incremental update) ----
        with open(zip_v2, "rb") as f:
            response_v2 = client.post(
                "/projects/upload",
                data={
                    "project_name": project_name,
                    "user_id": user_id
                },
                files={
                    "file": ("code_collab_proj_v2.zip", f, "application/zip")
                },
            )

        assert response_v2.status_code == 200
        data_v2 = response_v2.json()

        # The same project should appear in "created" or "skipped"
        created_projects = data_v2.get("created", [])
        skipped_projects = data_v2.get("skipped", [])

        all_project_ids = [p["project_id"] for p in created_projects + skipped_projects]

        # Ensure the same project ID is present (incremental)
        assert project_id in all_project_ids

        # Optional: ensure only one project was created, others are skipped
        assert len([p for p in created_projects if p["project_id"] == project_id]) <= 1

def test_resume_edit(client: TestClient):
    # 1. Consent
    r = client.post("/privacy-consent", json={
        "user_id": None,
        "consent_type": "data_access",
        "granted": True,
        "version": 1
    })
    user_id = r.json()["user_id"]

    # 2. Upload project
    with open("tests/data/code_collab_proj_v1.zip", "rb") as f:
        upload = client.post(
            "/projects/upload",
            data={"user_id": user_id, "project_name": "req32-resume"},
            files={"file": ("p.zip", f, "application/zip")},
        )
    assert upload.status_code == 200

    # 3. Get a project_id from uploaded projects (created or skipped)
    created_projects = upload.json().get("created", [])
    skipped_projects = upload.json().get("skipped", [])
    all_projects = created_projects + skipped_projects
    assert len(all_projects) > 0, "No projects found to generate resume"
    project_id = all_projects[0]["project_id"]

    # 4. Generate resume using project_id
    gen = client.post("/resume/generate", json={"project_id": project_id})
    assert gen.status_code == 200

    resume_json = gen.json()
    resume_id = resume_json.get("resume_id")
    assert resume_id is not None, "resume_id should be returned"

    # 5. Edit the resume
    edit = client.post(f"/resume/{resume_id}/edit", json={
        "summary_text": "Edited summary",
        "resume_bullets": ["Edited bullet 1", "Edited bullet 2"]
    })
    assert edit.status_code == 200

    content = edit.json()["content"]
    assert content["summary_text"] == "Edited summary"
    assert content["resume_bullets"] == ["Edited bullet 1", "Edited bullet 2"]

def test_portfolio_edit(client):
    # 1. Consent
    r = client.post("/privacy-consent", json={
        "user_id": None,
        "consent_type": "data_access",
        "granted": True,
        "version": 1
    })
    user_id = r.json()["user_id"]

    # 2. Upload
    with open("tests/data/code_collab_proj_v1.zip", "rb") as f:
        upload = client.post(
            "/projects/upload",
            data={"user_id": user_id, "project_name": "req32-portfolio"},
            files={"file": ("p.zip", f, "application/zip")},
        )

    # 3. Get portfolio
    projects = client.get(f"/projects?user_id={user_id}").json()
    portfolio_id = projects["portfolio_id"]

    # 4. Generate portfolio
    gen = client.post("/portfolio/generate", json={"portfolio_id": portfolio_id})
    showcase_id = gen.json()["showcase_ids"][0]

    # 5. Edit showcase
    edit = client.post(
        f"/portfolio/{showcase_id}/edit",
        json={
            "title": "Edited Title",
            "summary_text": "Edited portfolio summary"
        }
    )

    assert edit.status_code == 200
    data = edit.json()
    assert data["content"]["title"] == "Edited Title"
    assert data["content"]["summary_text"] == "Edited portfolio summary"


#------------------------------
# Github Tests 
# -----------------------------

# -----------------------------
# Helper: create a zipped Git repo
# -----------------------------
def create_git_repo_zip(zip_path: str):
    tmpdir = tempfile.mkdtemp()  # temp dir for repo
    try:
        # Init repo with initial_branch = main to ensure consistency across systems
        repo = Repo.init(tmpdir, initial_branch='main')

        # Add a file and commit
        file_path = os.path.join(tmpdir, "file.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        repo.index.add(["file.txt"])
        repo.index.commit("initial commit")

        # Zip the folder INCLUDING .git
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, tmpdir)
                    zf.write(abs_path, rel_path)
    finally:
        # Cleanup temp repo folder
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# -----------------------------
# Test
# -----------------------------
def test_extract_commits_from_git_zip():
    tmpzip_path = os.path.join(tempfile.gettempdir(), "tmp_git_repo.zip")
    create_git_repo_zip(tmpzip_path)

    commits = extract_commits_from_git_zip(tmpzip_path)
    assert commits == ["initial commit"]

    os.remove(tmpzip_path)  # cleanup



# -----------------------------
# Github Commit Counts Tests
# -----------------------------

# -----------------------------
# Helper: create a git repo zip with multiple authors and commits
# -----------------------------
def create_git_repo_zip_with_authors(zip_path: str):
    tmpdir = tempfile.mkdtemp()
    try:
        repo = Repo.init(tmpdir, initial_branch='main')

        from git import Actor
        alice = Actor("Alice", "alice@example.com")
        bob = Actor("Bob", "bob@example.com")

        # Alice commits
        file1 = os.path.join(tmpdir, "file1.txt")
        with open(file1, "w") as f:
            f.write("commit 1 by Alice")
        repo.index.add(["file1.txt"])
        repo.index.commit("Commit 1", author=alice)

        # Bob commits
        file2 = os.path.join(tmpdir, "file2.txt")
        with open(file2, "w") as f:
            f.write("commit 2 by Bob")
        repo.index.add(["file2.txt"])
        repo.index.commit("Commit 2", author=bob)

        # Zip the folder INCLUDING .git
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, tmpdir)
                    zf.write(abs_path, rel_path)
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

# -----------------------------
# Test: commit counts extraction
# -----------------------------
def test_extract_commit_counts_from_git_zip():
    tmpzip_path = os.path.join(tempfile.gettempdir(), "tmp_git_repo.zip")
    create_git_repo_zip_with_authors(tmpzip_path)

    counts = extract_commit_counts_from_git_zip(tmpzip_path)
    assert counts["Alice"] == 1
    assert counts["Bob"] == 1

    os.remove(tmpzip_path)


def test_pdf_with_thumbnail_contains_image():
    # 1. Setup paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "data", "thumbnail.png")

    # 2. Read the image and encode it to Base64
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # 3. Construct the item matching the exact expected schema
    resume_item = {
        "resume_id": "test1",
        "content": {
            "project": {"name": "Test Project"},
            "summary_text": "This is a test summary",
            "resume_bullets": ["Bullet 1", "Bullet 2"],
            "thumbnail_blob": { 
                "data_base64": base64_image,
                "mime_type": "image/png"     
            }
        }
    }

    # 4. Run the export
    pdf_bytes = export_resume_item_pdf_bytes(resume_item)

    # 5. Assertions
    assert pdf_bytes.startswith(b"%PDF"), "Output is not a PDF"
    # This checks for the existence of the image object in the PDF binary
    assert b"/XObject" in pdf_bytes or b"/Image" in pdf_bytes, "Thumbnail image not embedded"


# --- Test case 2: PDF without thumbnail ---
def test_pdf_without_thumbnail_no_image_marker():
    resume_item = {
        "resume_id": "test2",
        "content": {
            "project": {"name": "No Image Project"},
            "summary_text": "No image here",
            "resume_bullets": ["Bullet 1"],
        }
    }

    pdf_bytes = export_resume_item_pdf_bytes(resume_item)
    assert pdf_bytes.startswith(b"%PDF"), "Output is not a PDF"

    # Ensure no image stream is present
    assert b"/XObject" not in pdf_bytes, "Unexpected image embedded"