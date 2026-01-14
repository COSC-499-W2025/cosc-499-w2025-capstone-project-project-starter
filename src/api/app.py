from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from src.db.session import get_engine

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
async def upload_project(file: UploadFile = File(...)):
    # Placeholder: ingestion will be implemented next (zip parse -> projects/snapshots/file_blobs)
    # For now, ensure the endpoint exists per Milestone 2.
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip upload")
    _ = await file.read()
    return {"accepted": True, "filename": file.filename}


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
