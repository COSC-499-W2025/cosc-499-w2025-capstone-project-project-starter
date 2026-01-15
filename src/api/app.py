from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel
from sqlalchemy import text

import os

from src.db.session import get_engine
from src.api.ingest import ingest_zip_to_db, save_upload_to_temp
from src.api.report import build_project_report
from src.db.consents import get_snapshot_owner_user_id, is_external_services_allowed


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
        if payload.user_id is None:
            user_id = conn.execute(text("INSERT INTO users DEFAULT VALUES RETURNING id")).scalar_one()
        else:
            user_id = payload.user_id

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
    finally:
        try:
            os.unlink(tmp_zip)
        except Exception:
            pass


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
    engine = get_engine()
    with engine.connect() as conn:
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


@app.post("/snapshots/{snapshot_id}/external-analysis")
def request_external_analysis(snapshot_id: str):
    """
    Triggers external analysis if and only if external_services consent is granted
    for the owning user of the snapshot.

    If not granted, this endpoint returns/ensures the local ML alternative.
    """
    engine = get_engine()
    with engine.begin() as conn:
        uid = get_snapshot_owner_user_id(conn, snapshot_id)
        if not uid:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        allowed = is_external_services_allowed(conn, str(uid))

        if not allowed:
            # Alternative analysis: local ML.
            # If a local_ml job exists, return its status; else enqueue it.
            row = conn.execute(
                text(
                    """
                    SELECT id, status
                    FROM analyses
                    WHERE snapshot_id = :sid AND analysis_type = 'local_ml'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"sid": snapshot_id},
            ).mappings().first()

            if not row:
                aid = conn.execute(
                    text(
                        """
                        INSERT INTO analyses (snapshot_id, analysis_type, status)
                        VALUES (:sid, 'local_ml', 'pending')
                        RETURNING id
                        """
                    ),
                    {"sid": snapshot_id},
                ).scalar_one()
                return {
                    "snapshot_id": snapshot_id,
                    "external_allowed": False,
                    "used": "local_ml",
                    "analysis_id": str(aid),
                    "status": "pending",
                }

            return {
                "snapshot_id": snapshot_id,
                "external_allowed": False,
                "used": "local_ml",
                "analysis_id": str(row["id"]),
                "status": row["status"],
            }

        # Consent granted: ensure external_llm analysis exists (enqueue if missing).
        row = conn.execute(
            text(
                """
                SELECT id, status
                FROM analyses
                WHERE snapshot_id = :sid AND analysis_type = 'external_llm'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"sid": snapshot_id},
        ).mappings().first()

        if row:
            return {
                "snapshot_id": snapshot_id,
                "external_allowed": True,
                "used": "external_llm",
                "analysis_id": str(row["id"]),
                "status": row["status"],
            }

        aid = conn.execute(
            text(
                """
                INSERT INTO analyses (snapshot_id, analysis_type, status)
                VALUES (:sid, 'external_llm', 'pending')
                RETURNING id
                """
            ),
            {"sid": snapshot_id},
        ).scalar_one()

        return {
            "snapshot_id": snapshot_id,
            "external_allowed": True,
            "used": "external_llm",
            "analysis_id": str(aid),
            "status": "pending",
        }


@app.get("/snapshots/{snapshot_id}/external-analysis")
def get_external_analysis(snapshot_id: str):
    """
    Returns the latest external_llm analysis output if complete.
    If consent is not granted, returns the latest local_ml analysis output if complete.
    """
    engine = get_engine()
    with engine.connect() as conn:
        uid = get_snapshot_owner_user_id(conn, snapshot_id)
        if not uid:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        allowed = is_external_services_allowed(conn, str(uid))

        if allowed:
            row = conn.execute(
                text(
                    """
                    SELECT id, status, output_json
                    FROM analyses
                    WHERE snapshot_id = :sid AND analysis_type = 'external_llm'
                    ORDER BY completed_at DESC NULLS LAST, created_at DESC
                    LIMIT 1
                    """
                ),
                {"sid": snapshot_id},
            ).mappings().first()
            if not row:
                return {"snapshot_id": snapshot_id, "external_allowed": True, "analysis": None}
            return {"snapshot_id": snapshot_id, "external_allowed": True, "analysis": dict(row)}

        # Fallback: local_ml
        row = conn.execute(
            text(
                """
                SELECT id, status, output_json
                FROM analyses
                WHERE snapshot_id = :sid AND analysis_type = 'local_ml'
                ORDER BY completed_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
            ),
            {"sid": snapshot_id},
        ).mappings().first()
        if not row:
            return {"snapshot_id": snapshot_id, "external_allowed": False, "analysis": None}
        return {"snapshot_id": snapshot_id, "external_allowed": False, "analysis": dict(row)}


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


# Placeholders for milestone-2 endpoints
@app.post("/resume/generate")
def generate_resume():
    return {"accepted": True}


@app.post("/resume/{resume_id}/edit")
def edit_resume(resume_id: str):
    return {"accepted": True}


@app.get("/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, user_id, name, created_at FROM portfolios WHERE id = :id"),
            {"id": portfolio_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Portfolio not found")
    return dict(row)


@app.post("/portfolio/generate")
def generate_portfolio():
    return {"accepted": True}


@app.post("/portfolio/{portfolio_id}/edit")
def edit_portfolio(portfolio_id: str):
    return {"accepted": True}
