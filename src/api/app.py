from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from src.db.session import get_engine
import os
from fastapi import Form
from src.api.ingest import ingest_zip_to_db, save_upload_to_temp
import zipfile
from fastapi import Query
from src.api.report import build_project_report

app = FastAPI(title="Artifact Miner API", version="0.1.0")


class PrivacyConsentIn(BaseModel):
    user_id: str | None = None
    consent_type: str  # data_access | external_services
    granted: bool
    version: int = 1


@app.get("/health")
def health():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"ok": True}


@app.post("/privacy-consent")
def post_privacy_consent(payload: PrivacyConsentIn):
    engine = get_engine()
    with engine.begin() as conn:
        # Ensure a user exists (single-user default if none provided)
        if payload.user_id is None:
            user_id = conn.execute(text("INSERT INTO users DEFAULT VALUES RETURNING id")).scalar_one()
        else:
            user_id = payload.user_id

        # Upsert consent (simple insert; upgrades can coalesce by (user_id, consent_type))
        conn.execute(
            text(
                """
                INSERT INTO privacy_consents (user_id, consent_type, granted, version, granted_at, revoked_at)
                VALUES (:user_id, :ctype, :granted, :version,
                        CASE WHEN :granted THEN NOW() ELSE NULL END,
                        CASE WHEN :granted THEN NULL ELSE NOW() END)
                """
            ),
            {"user_id": user_id, "ctype": payload.consent_type, "granted": payload.granted, "version": payload.version},
        )

        # Ensure user_config exists
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

    return {"user_id": str(user_id), "consent_type": payload.consent_type, "granted": payload.granted}


@app.post("/projects/upload")
async def upload_project(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    portfolio_id: str | None = Form(default=None),
    project_name: str | None = Form(default=None),
    snapshot_label: str | None = Form(default=None),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip upload")

    upload_bytes = await file.read()
    if not upload_bytes:
        raise HTTPException(status_code=400, detail="Empty upload")

    tmp_zip = save_upload_to_temp(upload_bytes)
    try:
        blobstore_root = os.environ.get("ARTIFACT_MINER_BLOBSTORE", "/blobstore")
        res = ingest_zip_to_db(
            engine=get_engine(),
            zip_path=tmp_zip,
            zip_filename=file.filename,
            blobstore_root=blobstore_root,
            user_id=user_id,
            portfolio_id=portfolio_id,
            project_name=project_name,
            snapshot_label=snapshot_label,
        )
        return {
            "user_id": res.user_id,
            "portfolio_id": res.portfolio_id,
            "created": res.created_projects,
            "skipped": res.skipped_projects,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    finally:
        try:
            os.remove(tmp_zip)
        except OSError:
            pass



@app.get("/projects")
def list_projects():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name, project_type, collaboration_type, created_at FROM projects ORDER BY created_at ASC")).mappings().all()
    return {"projects": list(rows)}


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM projects WHERE id = :id"), {"id": project_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.get("/skills")
def list_skills():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT skill_name, category FROM skills ORDER BY skill_name ASC")).mappings().all()
    return {"skills": list(rows)}


@app.get("/resume/{resume_id}")
def get_resume(resume_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, project_id, content_json, updated_at FROM resume_items WHERE id = :id"), {"id": resume_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Resume item not found")
    return dict(row)


@app.post("/resume/generate")
def generate_resume():
    # Placeholder
    return {"accepted": True}


@app.post("/resume/{resume_id}/edit")
def edit_resume(resume_id: str):
    return {"accepted": True}


@app.get("/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, user_id, name, created_at FROM portfolios WHERE id = :id"), {"id": portfolio_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Portfolio not found")
    return dict(row)


@app.post("/portfolio/generate")
def generate_portfolio():
    return {"accepted": True}


@app.post("/portfolio/{portfolio_id}/edit")
def edit_portfolio(portfolio_id: str):
    return {"accepted": True}

@app.get("/snapshots/{snapshot_id}/analyses")
def list_snapshot_analyses(snapshot_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                  id,
                  analysis_type,
                  status,
                  started_at,
                  completed_at,
                  COALESCE(output_json->>'error', NULL) AS error
                FROM analyses
                WHERE snapshot_id = :sid
                ORDER BY created_at ASC
                """
            ),
            {"sid": snapshot_id},
        ).mappings().all()
    return {"snapshot_id": snapshot_id, "analyses": [dict(r) for r in rows]}


@app.get("/snapshots/{snapshot_id}/skills")
def list_snapshot_skills(snapshot_id: str, limit: int = Query(default=20, ge=1, le=200)):
    """
    Returns skills detected for a snapshot, based on the completed local_ml analysis.
    """
    engine = get_engine()
    with engine.connect() as conn:
        # Find the local_ml analysis for this snapshot
        aid = conn.execute(
            text(
                """
                SELECT id
                FROM analyses
                WHERE snapshot_id = :sid AND analysis_type = 'local_ml' AND status = 'complete'
                ORDER BY completed_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
            ),
            {"sid": snapshot_id},
        ).scalar()

        if not aid:
            return {"snapshot_id": snapshot_id, "analysis_id": None, "skills": []}

        rows = conn.execute(
            text(
                """
                SELECT
                  s.skill_name,
                  s.category,
                  a_s.confidence
                FROM analysis_skills a_s
                JOIN skills s ON s.id = a_s.skill_id
                WHERE a_s.analysis_id = :aid
                ORDER BY a_s.confidence DESC, s.skill_name ASC
                LIMIT :lim
                """
            ),
            {"aid": str(aid), "lim": int(limit)},
        ).mappings().all()

    return {"snapshot_id": snapshot_id, "analysis_id": str(aid), "skills": [dict(r) for r in rows]}

@app.get("/projects/{project_id}/report")
def get_project_report(
    project_id: str,
    include_raw_analyses: bool = Query(default=False),
    include_framework_detection: bool = Query(default=True),
):
    engine = get_engine()
    try:
        report = build_project_report(
            engine=engine,
            project_id=project_id,
            include_raw_analyses=bool(include_raw_analyses),
            include_framework_detection=bool(include_framework_detection),
        )
        return report
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")