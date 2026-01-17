import uuid
from datetime import datetime, timezone
import io
import zipfile

from sqlalchemy import text
import re
import json
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB


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
    
    # --- FIX: Set the specific environment variable the app looks for ---
    test_blob_dir = tmp_path / "test_blobs"
    test_blob_dir.mkdir()
    
    # This matches the key found in src/api/app.py line 139
    monkeypatch.setenv("ARTIFACT_MINER_BLOBSTORE", str(test_blob_dir))
    # ------------------------------------------------------------------
    
    # 1. Create a user and grant consent
    r_consent = client.post(
        "/privacy-consent",
        json={"consent_type": "data_access", "granted": True, "version": 1},
    )
    assert r_consent.status_code == 200
    user_id = r_consent.json()["user_id"]

    # 2. Upload a project
    # (We use the helper to make a fake zip in memory)
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

    # 3. UPDATE (Patch) the Display Name
    new_name = "My Polished Project"
    r_patch = client.patch(
        f"/projects/{project_id}",
        json={"display_name": new_name}
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["display_name"] == new_name

    # 4. Generate Resume
    # This verifies the SQL query uses COALESCE(display_name, name)
    r_resume = client.post(
        "/resume/generate",
        json={"project_id": project_id, "prefer_external_bullets": False}
    )
    assert r_resume.status_code == 200
    
    # 5. Verify the PDF content data
    content = r_resume.json()["content"]
    assert content["project"]["name"] == new_name
    assert content["project"]["name"] != "ugly_filename_v1.zip"
