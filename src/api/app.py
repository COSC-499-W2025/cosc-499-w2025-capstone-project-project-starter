
from __future__ import annotations

import base64
from collections import Counter
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import zipfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID as PyUUID

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from git import InvalidGitRepositoryError, Repo
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Session

from src.api.ingest import assign_roles, extract_commits_from_git_zip, find_git_repo, ingest_zip_to_db, save_upload_to_temp
from src.api.report import build_project_report
from src.db.consents import get_snapshot_owner_user_id, is_external_services_allowed
from src.db.session import get_db, get_engine
from src.db.base import FileBlob, PortfolioShowcase, Project

from src.db.user_config import (
    get_user_config,
    put_user_config,
    merge_user_config,
    identity_rules_for_user,
    resolve_project_owner_user_id,
    set_project_user_contributor_mapping,
    clear_project_user_contributor_mapping,
)

from src.api.ranking import compute_rank_score, normalize_ranking_config, sort_projects

from src.api.pdf_exporter import export_resume_item_pdf_bytes

from src.api.generation import (
    generate_portfolio_top_summaries,
    generate_resume_item,
    list_portfolio_showcases,
    get_resume_item,
)

from src.db.deletion import (
    delete_snapshot_and_gc,
    delete_portfolio_showcase_and_gc,
    delete_resume_item,
    delete_analysis,
)


app = FastAPI(title="Artifact Miner API", version="0.1.0")

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://host.docker.internal:3000",
]
origins_env = os.environ.get("CORS_ALLOW_ORIGINS")
origins = [o.strip() for o in origins_env.split(",") if o.strip()] if origins_env else default_origins

# CORS middleware - adjust for production as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PrivacyConsentIn(BaseModel):
    user_id: str | None = None
    consent_type: str  # data_access | external_services
    granted: bool
    version: int = 1


class UserConfigOut(BaseModel):
    user_id: str
    config: Dict[str, Any]


class UserConfigIn(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)


class SetUserContributorIn(BaseModel):
    is_user: bool = True
    unset_others: bool = True
    persist_to_config: bool = True

class ProjectUpdateIn(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=255)
    user_role: Optional[str] = Field(default=None, max_length=128)
    evidence_json: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    feedback: Optional[Any] = None
    evaluation: Optional[Any] = None

class ResumeGenerateIn(BaseModel):
    project_id: str
    prefer_external_bullets: Optional[bool] = True

class ProjectImagePath(BaseModel):
    filepath: str

class ResumeEditRequest(BaseModel):
    summary_text: Optional[str] = None
    resume_bullets: Optional[List[str]] = None

class PortfolioEditRequest(BaseModel):
    title: Optional[str] = None
    summary_text: Optional[str] = None

class AuthRegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: Optional[str] = Field(default=None, max_length=200)
    consent_data_access: bool = True

class AuthLoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

AUTH_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
SESSION_TTL_DAYS = max(1, int(os.environ.get("AUTH_SESSION_TTL_DAYS", "14")))
auth_bearer = HTTPBearer(auto_error=False)

def _normalize_email(email: str) -> str:
    return str(email or "").strip().casefold()

def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _b64u_decode(raw: str) -> bytes:
    pad = "=" * ((4 - (len(raw) % 4)) % 4)
    return base64.urlsafe_b64decode(raw + pad)

def _hash_password(password: str) -> str:
    if len(password or "") < PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    iterations = 260_000
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64u_encode(salt)}${_b64u_encode(digest)}"

def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iter_s, salt_s, hash_s = (encoded or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        salt = _b64u_decode(salt_s)
        expected = _b64u_decode(hash_s)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _issue_session() -> Tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    return token, token_hash, expires_at

def _ensure_user_config_row(conn, user_id: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO user_config (user_id, config_json)
            VALUES (:uid, '{}'::jsonb)
            ON CONFLICT (user_id) DO NOTHING
            """
        ),
        {"uid": user_id},
    )

def _ensure_default_portfolio(conn, user_id: str) -> str:
    existing = conn.execute(
        text(
            """
            SELECT id
            FROM portfolios
            WHERE user_id = :uid AND name = 'default'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        {"uid": user_id},
    ).scalar()
    if existing:
        return str(existing)
    created = conn.execute(
        text("INSERT INTO portfolios (user_id, name) VALUES (:uid, 'default') RETURNING id"),
        {"uid": user_id},
    ).scalar_one()
    return str(created)

def _portfolio_owner_user_id(conn, portfolio_id: str) -> Optional[str]:
    owner = conn.execute(
        text("SELECT user_id FROM portfolios WHERE id = :pid"),
        {"pid": portfolio_id},
    ).scalar()
    return str(owner) if owner else None

def _assert_portfolio_owned_by(conn, *, portfolio_id: str, user_id: str) -> None:
    owner = _portfolio_owner_user_id(conn, portfolio_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if owner != str(user_id):
        raise HTTPException(status_code=403, detail="Portfolio does not belong to the authenticated user")

def _auth_user_payload(user_id: str, email: str, display_name: Optional[str], portfolio_id: Optional[str]) -> Dict[str, Any]:
    return {
        "user_id": str(user_id),
        "email": email,
        "display_name": display_name,
        "portfolio_id": str(portfolio_id) if portfolio_id else None,
    }

def _resolve_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials],
    *,
    required: bool,
) -> Optional[Dict[str, Any]]:
    def _unauthorized() -> None:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token")

    if credentials is None:
        if required:
            _unauthorized()
        return None

    if credentials.scheme.lower() != "bearer":
        _unauthorized()

    token = (credentials.credentials or "").strip()
    if not token:
        _unauthorized()

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  s.user_id,
                  s.expires_at,
                  s.revoked_at,
                  a.email,
                  a.display_name,
                  p.id AS portfolio_id
                FROM auth_sessions s
                JOIN auth_accounts a ON a.user_id = s.user_id
                LEFT JOIN LATERAL (
                  SELECT id
                  FROM portfolios
                  WHERE user_id = s.user_id AND name = 'default'
                  ORDER BY created_at ASC
                  LIMIT 1
                ) p ON TRUE
                WHERE s.token_hash = :th
                """
            ),
            {"th": token_hash},
        ).mappings().first()

    now = datetime.now(timezone.utc)
    if (not row) or row.get("revoked_at") is not None or row.get("expires_at") is None or row["expires_at"] <= now:
        _unauthorized()

    return {
        "token": token,
        "token_hash": token_hash,
        "user_id": str(row["user_id"]),
        "email": row["email"],
        "display_name": row.get("display_name"),
        "portfolio_id": str(row["portfolio_id"]) if row.get("portfolio_id") else None,
    }

def _rank_score(user_commits: int, total_commits: int) -> Optional[float]:
    # Deterministic and transparent. Only meaningful if user_commits > 0.
    if user_commits <= 0:
        return None
    other = max(0, int(total_commits) - int(user_commits))
    return float(int(user_commits)) + 0.10 * float(other)

def _get_or_create_showcase(conn, project_id: str) -> str:
    sid = conn.execute(
        text(
            """
            SELECT id
            FROM portfolio_showcases
            WHERE project_id = :pid
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        {"pid": project_id},
    ).scalar()

    if sid:
        return str(sid)

    sid = conn.execute(
        text(
            """
            INSERT INTO portfolio_showcases (project_id, content_json)
            VALUES (:pid, '{}'::jsonb)
            RETURNING id
            """
        ),
        {"pid": project_id},
    ).scalar_one()

    return str(sid)


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


@app.post("/auth/register")
def auth_register(payload: AuthRegisterIn):
    email = _normalize_email(payload.email)
    if not AUTH_EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not payload.consent_data_access:
        raise HTTPException(status_code=400, detail="Data access consent is required to register")

    display_name = (payload.display_name or "").strip() or None
    password_hash = _hash_password(payload.password)

    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT user_id FROM auth_accounts WHERE LOWER(email) = :email LIMIT 1"),
            {"email": email},
        ).scalar()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(conn.execute(text("INSERT INTO users DEFAULT VALUES RETURNING id")).scalar_one())
        _ensure_user_config_row(conn, user_id)
        portfolio_id = _ensure_default_portfolio(conn, user_id)

        conn.execute(
            text(
                """
                INSERT INTO privacy_consents (user_id, consent_type, granted, version, granted_at, revoked_at)
                VALUES (:user_id, 'data_access', TRUE, 1, NOW(), NULL)
                """
            ),
            {"user_id": user_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO auth_accounts (user_id, email, password_hash, display_name)
                VALUES (:uid, :email, :pwd, :display_name)
                """
            ),
            {
                "uid": user_id,
                "email": email,
                "pwd": password_hash,
                "display_name": display_name,
            },
        )

        token, token_hash, expires_at = _issue_session()
        conn.execute(
            text(
                """
                INSERT INTO auth_sessions (token_hash, user_id, expires_at)
                VALUES (:th, :uid, :exp)
                """
            ),
            {"th": token_hash, "uid": user_id, "exp": expires_at},
        )

    return {
        "token": token,
        "expires_at": expires_at,
        "user": _auth_user_payload(user_id, email, display_name, portfolio_id),
    }


@app.post("/auth/login")
def auth_login(payload: AuthLoginIn):
    email = _normalize_email(payload.email)
    if not AUTH_EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="A valid email address is required")

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, password_hash, display_name
                FROM auth_accounts
                WHERE LOWER(email) = :email
                LIMIT 1
                """
            ),
            {"email": email},
        ).mappings().first()

        if not row or not _verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = str(row["user_id"])
        account_email = str(row["email"])
        account_display_name = row.get("display_name")
        portfolio_id = _ensure_default_portfolio(conn, user_id)
        token, token_hash, expires_at = _issue_session()
        conn.execute(
            text(
                """
                INSERT INTO auth_sessions (token_hash, user_id, expires_at)
                VALUES (:th, :uid, :exp)
                """
            ),
            {"th": token_hash, "uid": user_id, "exp": expires_at},
        )

    return {
        "token": token,
        "expires_at": expires_at,
        "user": _auth_user_payload(
            user_id=user_id,
            email=account_email,
            display_name=account_display_name,
            portfolio_id=portfolio_id,
        ),
    }


@app.get("/auth/me")
def auth_me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer)):
    auth = _resolve_auth_context(credentials, required=True)
    assert auth is not None
    return {"user": _auth_user_payload(auth["user_id"], auth["email"], auth.get("display_name"), auth.get("portfolio_id"))}


@app.post("/auth/logout")
def auth_logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer)):
    auth = _resolve_auth_context(credentials, required=True)
    assert auth is not None
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE auth_sessions
                SET revoked_at = NOW()
                WHERE token_hash = :th
                  AND revoked_at IS NULL
                """
            ),
            {"th": auth["token_hash"]},
        )
    return {"ok": True}


@app.post("/projects/upload")
async def upload_project(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    portfolio_id: str | None = Form(default=None),
    project_name: str | None = Form(default=None),
    snapshot_label: str | None = Form(default=None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    auth = _resolve_auth_context(credentials, required=False)
    if auth:
        if user_id and str(user_id) != auth["user_id"]:
            raise HTTPException(status_code=403, detail="Authenticated user does not match provided user_id")
        user_id = auth["user_id"]
        if portfolio_id:
            with get_engine().connect() as conn:
                _assert_portfolio_owned_by(conn, portfolio_id=portfolio_id, user_id=auth["user_id"])

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
                ORDER BY started_at ASC NULLS LAST, created_at ASC, id ASC
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

@app.get("/skills")
def list_all_skills(category: Optional[str] = Query(None)):
    """
    Returns a list of all unique skills from the global skills table.
    Optionally filterable by category.
    """
    engine = get_engine()
    with engine.connect() as conn:
        query = "SELECT id, skill_name, category FROM skills"
        params = {}
        
        if category:
            query += " WHERE category = :cat"
            params["cat"] = category
            
        query += " ORDER BY skill_name ASC"
        
        rows = conn.execute(text(query), params).mappings().all()
        
    return {"skills": [dict(r) for r in rows]}

@app.post("/snapshots/{snapshot_id}/external-analysis")
def request_external_analysis(snapshot_id: str):
    engine = get_engine()
    with engine.begin() as conn:
        uid = get_snapshot_owner_user_id(conn, snapshot_id)
        if not uid:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        allowed = is_external_services_allowed(conn, str(uid))

        if not allowed:
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



@app.get("/users/{user_id}/config", response_model=UserConfigOut)
def get_config(user_id: str):
    engine = get_engine()
    with engine.begin() as conn:
        cfg = get_user_config(conn, user_id)
    return {"user_id": user_id, "config": cfg}


@app.put("/users/{user_id}/config", response_model=UserConfigOut)
def put_config(user_id: str, payload: UserConfigIn):
    engine = get_engine()
    with engine.begin() as conn:
        cfg = put_user_config(conn, user_id, payload.config or {})
    return {"user_id": user_id, "config": cfg}


@app.patch("/users/{user_id}/config", response_model=UserConfigOut)
def patch_config(user_id: str, patch: Dict[str, Any] = Body(default_factory=dict)):
    engine = get_engine()
    with engine.begin() as conn:
        cfg = merge_user_config(conn, user_id, patch or {})
    return {"user_id": user_id, "config": cfg}


@app.get("/projects/{project_id}/contributors")
def list_project_contributors(project_id: str):
    engine = get_engine()
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM projects WHERE id = :pid"), {"pid": project_id}).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Project not found")

        rows = conn.execute(
            text(
                """
                WITH contrib_commits AS (
                  SELECT
                    ce.contributor_id,
                    COALESCE(SUM(ce.commit_count), 0) AS commits
                  FROM contribution_events ce
                  JOIN snapshots s ON s.id = ce.snapshot_id
                  WHERE s.project_id = :pid
                  GROUP BY ce.contributor_id
                )
                SELECT
                  c.id AS contributor_id,
                  c.canonical_name,
                  c.email,
                  pc.is_user,
                  COALESCE(cc.commits, 0) AS commits
                FROM project_contributors pc
                JOIN contributors c ON c.id = pc.contributor_id
                LEFT JOIN contrib_commits cc ON cc.contributor_id = pc.contributor_id
                WHERE pc.project_id = :pid
                ORDER BY pc.is_user DESC, commits DESC, c.canonical_name ASC
                """
            ),
            {"pid": project_id},
        ).mappings().all()

    return {"project_id": project_id, "contributors": [dict(r) for r in rows]}


@app.post("/projects/{project_id}/contributors/{contributor_id}/set-user")
def set_project_user_contributor(project_id: str, contributor_id: str, payload: SetUserContributorIn):
    """
    Sets project_contributors.is_user and (optionally) persists to user_config:
      config.identity.project_contributor_map[project_id] = contributor_id
    """
    engine = get_engine()
    with engine.begin() as conn:
        proj = conn.execute(
            text("SELECT id FROM projects WHERE id = :pid"),
            {"pid": project_id},
        ).scalar()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        cid_ok = conn.execute(
            text("SELECT 1 FROM contributors WHERE id = :cid"),
            {"cid": contributor_id},
        ).scalar()
        if not cid_ok:
            raise HTTPException(status_code=404, detail="Contributor not found")

        # Ensure link exists.
        conn.execute(
            text(
                """
                INSERT INTO project_contributors (project_id, contributor_id, is_user)
                VALUES (:pid, :cid, FALSE)
                ON CONFLICT (project_id, contributor_id) DO NOTHING
                """
            ),
            {"pid": project_id, "cid": contributor_id},
        )

        if payload.unset_others:
            conn.execute(
                text(
                    """
                    UPDATE project_contributors
                    SET is_user = FALSE
                    WHERE project_id = :pid AND contributor_id <> :cid
                    """
                ),
                {"pid": project_id, "cid": contributor_id},
            )

        conn.execute(
            text(
                """
                UPDATE project_contributors
                SET is_user = :flag
                WHERE project_id = :pid AND contributor_id = :cid
                """
            ),
            {"pid": project_id, "cid": contributor_id, "flag": bool(payload.is_user)},
        )

        # Persist mapping into user_config so future git_metrics runs can auto-link deterministically.
        owner_user_id = resolve_project_owner_user_id(conn, project_id)
        if owner_user_id and payload.persist_to_config:
            if payload.is_user:
                set_project_user_contributor_mapping(conn, owner_user_id, project_id, contributor_id)
            else:
                clear_project_user_contributor_mapping(conn, owner_user_id, project_id)

    return {"project_id": project_id, "contributor_id": contributor_id, "is_user": bool(payload.is_user)}

@app.get("/projects")
def list_projects(
    portfolio_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    """
    Lists projects with derived ranking metrics.
    Requires either portfolio_id or user_id.
    If user_id is provided, uses the user's default portfolio (name='default') if it exists.
    """
    engine = get_engine()
    auth = _resolve_auth_context(credentials, required=False)
    with engine.connect() as conn:
        if auth:
            if user_id and str(user_id) != auth["user_id"]:
                raise HTTPException(status_code=403, detail="Authenticated user does not match provided user_id")
            user_id = auth["user_id"]
            if portfolio_id:
                _assert_portfolio_owned_by(conn, portfolio_id=portfolio_id, user_id=auth["user_id"])

        if not portfolio_id and not user_id:
            raise HTTPException(status_code=400, detail="Provide portfolio_id or user_id")

        if not portfolio_id and user_id:
            portfolio_id = conn.execute(
                text(
                    """
                    SELECT id
                    FROM portfolios
                    WHERE user_id = :uid AND name = 'default'
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ),
                {"uid": user_id},
            ).scalar()
            if not portfolio_id:
                return {"portfolio_id": None, "projects": []}
            portfolio_id = str(portfolio_id)

        rows = conn.execute(
            text(
                """
                WITH totals AS (
                  SELECT
                    s.project_id,
                    COALESCE(SUM(ce.commit_count), 0) AS total_commits,
                    COUNT(DISTINCT ce.contributor_id) AS contributor_count
                  FROM snapshots s
                  LEFT JOIN contribution_events ce ON ce.snapshot_id = s.id
                  GROUP BY s.project_id
                ),
                user_totals AS (
                  SELECT
                    s.project_id,
                    COALESCE(SUM(ce.commit_count), 0) AS user_commits
                  FROM snapshots s
                  JOIN contribution_events ce ON ce.snapshot_id = s.id
                  JOIN project_contributors pc
                    ON pc.project_id = s.project_id
                   AND pc.contributor_id = ce.contributor_id
                   AND pc.is_user = TRUE
                  GROUP BY s.project_id
                ),
                latest AS (
                  SELECT DISTINCT ON (project_id)
                    project_id,
                    id AS latest_snapshot_id,
                    ingested_at AS latest_ingested_at
                  FROM snapshots
                  ORDER BY project_id, ingested_at DESC
                )
                SELECT
                  pr.id,
                  pr.name,
                  pr.project_type,
                  pr.collaboration_type,
                  pr.user_role,
                  pr.created_at,
                  COALESCE(t.total_commits, 0) AS total_commits,
                  COALESCE(ut.user_commits, 0) AS user_commits,
                  COALESCE(t.contributor_count, 0) AS contributor_count,
                  l.latest_snapshot_id,
                  l.latest_ingested_at
                FROM projects pr
                LEFT JOIN totals t ON t.project_id = pr.id
                LEFT JOIN user_totals ut ON ut.project_id = pr.id
                LEFT JOIN latest l ON l.project_id = pr.id
                WHERE pr.portfolio_id = :pf
                ORDER BY pr.created_at ASC
                """
            ),
            {"pf": portfolio_id},
        ).mappings().all()

        portfolio_user_id = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        user_cfg = get_user_config(conn, str(portfolio_user_id)) if portfolio_user_id else {}
        ranking_cfg = normalize_ranking_config((user_cfg or {}).get("ranking") or {})

    out = []
    for r in rows:
        total = int(r["total_commits"] or 0)
        userc = int(r["user_commits"] or 0)
        userc_out = userc if userc > 0 else None
        rank_score = compute_rank_score(
            user_commits=userc_out,
            total_commits=total,
            contributor_count=int(r["contributor_count"] or 0),
            ranking_cfg=ranking_cfg,
        )
        out.append(
            {
                "id": str(r["id"]),
                "name": r["name"],
                "project_type": r["project_type"],
                "collaboration_type": r["collaboration_type"],
                "user_role": r.get("user_role"),
                "created_at": r["created_at"],
                "metrics": {
                    "total_commits": total,
                    "user_commits": userc_out,
                    "contributor_count": int(r["contributor_count"] or 0),
                    "rank_score": rank_score,
                },
                "latest_snapshot": {
                    "id": str(r["latest_snapshot_id"]) if r.get("latest_snapshot_id") else None,
                    "ingested_at": r.get("latest_ingested_at"),
                },
            }
        )

    out = sort_projects(out, ranking_cfg)

    return {"portfolio_id": str(portfolio_id), "projects": out}

@app.get("/projects/compare")
def compare_projects(
    project_ids: List[str] = Query(..., min_length=1),
    attributes: Optional[List[str]] = Query(default=None),
):
    """Compare a set of projects using user-selected attributes.

    Attribute selection precedence:
      1) explicit `attributes` query params
      2) user_config.comparison.attributes (portfolio owner)
      3) default set
    """
    engine = get_engine()

    # Normalize ids (allow both repeated query params and a single comma-separated entry).
    ids: List[str] = []
    for v in project_ids:
        if not v:
            continue
        if "," in v:
            ids.extend([x.strip() for x in v.split(",") if x.strip()])
        else:
            ids.append(v.strip())
    ids = [x for x in ids if x]
    if not ids:
        raise HTTPException(status_code=400, detail="Provide at least one project_id")

    with engine.connect() as conn:
        meta_rows = conn.execute(
            text(
                """
                SELECT p.id, p.portfolio_id, COALESCE(p.display_name, p.name) AS name,
                       p.project_type, p.collaboration_type, p.user_role
                FROM projects p
                WHERE p.id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        ).mappings().all()

        if len(meta_rows) != len(set(ids)):
            found = {str(r["id"]) for r in meta_rows}
            missing = [pid for pid in ids if pid not in found]
            raise HTTPException(status_code=404, detail={"missing_project_ids": missing})

        portfolio_ids = {str(r["portfolio_id"]) for r in meta_rows}
        if len(portfolio_ids) != 1:
            raise HTTPException(status_code=400, detail="All compared projects must belong to the same portfolio")
        portfolio_id = next(iter(portfolio_ids))

        portfolio_user_id = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        user_cfg = get_user_config(conn, str(portfolio_user_id)) if portfolio_user_id else {}

    cfg_comp = (user_cfg or {}).get("comparison") or {}
    cfg_ch = (user_cfg or {}).get("chronology") or {}
    highlight_skills = ((user_cfg or {}).get("highlights") or {}).get("skills") or []
    highlight_cf = {str(x).casefold() for x in highlight_skills if str(x).strip()}

    # Default attribute set (kept small but useful for side-by-side UI).
    default_attrs = [
        "meta",
        "duration",
        "contributions",
        "languages",
        "frameworks",
        "skills_top",
        "ranking",
    ]

    attrs: List[str]
    if attributes is not None and len(attributes) > 0:
        attrs = []
        for v in attributes:
            if not v:
                continue
            if "," in v:
                attrs.extend([x.strip() for x in v.split(",") if x.strip()])
            else:
                attrs.append(v.strip())
    else:
        attrs = [str(x) for x in (cfg_comp.get("attributes") or []) if str(x).strip()] or list(default_attrs)

    # case-insensitive override maps
    skill_override = {str(k).casefold(): str(v) for k, v in (cfg_ch.get("skill_first_seen") or {}).items()}
    proj_date_override = {str(k): str(v) for k, v in (cfg_ch.get("project_dates") or {}).items()}

    # Build reports and select attributes.
    per_project: List[Dict[str, Any]] = []
    for pid in ids:
        rep = build_project_report(engine=engine, project_id=pid, include_raw_analyses=False, include_framework_detection=True)

        latest_parser = None
        try:
            snaps = rep.get("snapshots") or []
            if snaps:
                latest_parser = ((snaps[-1].get("analyses") or {}).get("parser") or {})
        except Exception:
            latest_parser = None

        derived = rep.get("derived") or {}
        out: Dict[str, Any] = {"project_id": pid}

        if "meta" in attrs:
            out["meta"] = rep.get("project")

        if "duration" in attrs:
            dur = (derived.get("project_duration") or {}).copy()
            # If the user supplied a project date override, surface it without mutating snapshots.
            if pid in proj_date_override:
                dur["override_sort_ts"] = proj_date_override[pid]
            out["duration"] = dur

        if "contributions" in attrs:
            out["contributions"] = (derived.get("contributions") or {}).copy()

        if "languages" in attrs:
            out["languages"] = (latest_parser or {}).get("top_languages") or []

        if "activity_counts" in attrs:
            out["activity_counts"] = (latest_parser or {}).get("activity_counts") or None

        if "frameworks" in attrs:
            out["frameworks"] = ((derived.get("frameworks") or {}).get("frameworks") or [])

        if "skills_top" in attrs or "skills_chronological" in attrs:
            skills_obj = (derived.get("skills") or {})
            top = skills_obj.get("top") or []

            # Apply skill first-seen overrides (if requested) to the returned skill objects.
            def _apply_skill_override(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                out_rows: List[Dict[str, Any]] = []
                for r in rows:
                    rr = dict(r)
                    nm = str(rr.get("skill") or "")
                    ov = skill_override.get(nm.casefold())
                    if ov:
                        rr["first_seen_ts"] = ov
                        rr["overridden"] = True
                    rr["is_highlight"] = nm.casefold() in highlight_cf
                    out_rows.append(rr)
                return out_rows

            if "skills_top" in attrs:
                out["skills_top"] = _apply_skill_override([dict(x) for x in top[:25]])
            if "skills_chronological" in attrs:
                chrono = skills_obj.get("chronological") or []
                out["skills_chronological"] = _apply_skill_override([dict(x) for x in chrono[:100]])

        if "ranking" in attrs:
            out["ranking"] = (derived.get("ranking") or {}).copy()

        if "evidence" in attrs:
            out["evidence"] = (rep.get("project") or {}).get("evidence_json") or {}

        per_project.append(out)

    return {
        "portfolio_id": portfolio_id,
        "project_ids": ids,
        "attributes": attrs,
        "highlight_skills": highlight_skills,
        "projects": per_project,
    }

@app.get("/projects/{project_id}")
def get_project_by_id(project_id: str):
    """
    Retrieves full details for a single project by its ID.
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                WITH totals AS (
                  SELECT
                    s.project_id,
                    COALESCE(SUM(ce.commit_count), 0) AS total_commits,
                    COUNT(DISTINCT ce.contributor_id) AS contributor_count
                  FROM snapshots s
                  LEFT JOIN contribution_events ce ON ce.snapshot_id = s.id
                  WHERE s.project_id = :pid
                  GROUP BY s.project_id
                ),
                user_totals AS (
                  SELECT
                    s.project_id,
                    COALESCE(SUM(ce.commit_count), 0) AS user_commits
                  FROM snapshots s
                  JOIN contribution_events ce ON ce.snapshot_id = s.id
                  JOIN project_contributors pc
                    ON pc.project_id = s.project_id
                   AND pc.contributor_id = ce.contributor_id
                   AND pc.is_user = TRUE
                  WHERE s.project_id = :pid
                  GROUP BY s.project_id
                ),
                latest AS (
                  SELECT 
                    id AS latest_snapshot_id,
                    ingested_at AS latest_ingested_at
                  FROM snapshots
                  WHERE project_id = :pid
                  ORDER BY ingested_at DESC
                  LIMIT 1
                )
                SELECT
                  pr.id,
                  pr.portfolio_id,
                  pr.name,
                  pr.display_name,
                  pr.project_type,
                  pr.collaboration_type,
                  pr.user_role,
                  pr.created_at,
                  COALESCE(t.total_commits, 0) AS total_commits,
                  COALESCE(ut.user_commits, 0) AS user_commits,
                  COALESCE(t.contributor_count, 0) AS contributor_count,
                  l.latest_snapshot_id,
                  l.latest_ingested_at
                FROM projects pr
                LEFT JOIN totals t ON t.project_id = pr.id
                LEFT JOIN user_totals ut ON ut.project_id = pr.id
                LEFT JOIN latest l ON 1=1
                WHERE pr.id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        # Convert to dict and format metrics as seen in list_projects
        res = dict(row)
        res["metrics"] = {
            "total_commits": int(res.pop("total_commits")),
            "user_commits": int(res.pop("user_commits")) or None,
            "contributor_count": int(res.pop("contributor_count")),
        }
        res["latest_snapshot"] = {
            "id": str(res.pop("latest_snapshot_id")) if res.get("latest_snapshot_id") else None,
            "ingested_at": res.pop("latest_ingested_at"),
        }
        
    return res

@app.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdateIn):
    """
    Partial project metadata update.
    Supports display_name, user_role, and evidence fields.
    """
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT 1 FROM projects WHERE id = :pid"),
            {"pid": project_id}
        ).scalar()

        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No update fields provided")

        if "evidence_json" in updates and "evidence" in updates:
            raise HTTPException(status_code=400, detail="Provide either evidence_json or evidence, not both")

        set_clauses: List[str] = []
        params: Dict[str, Any] = {"pid": project_id}

        if "display_name" in updates:
            set_clauses.append("display_name = :display_name")
            params["display_name"] = updates["display_name"]

        if "user_role" in updates:
            set_clauses.append("user_role = :user_role")
            params["user_role"] = updates["user_role"]

        evidence_keys = {"evidence_json", "evidence", "metrics", "feedback", "evaluation"}
        evidence_payload_present = any(k in updates for k in evidence_keys)
        if evidence_payload_present:
            if "evidence_json" in updates:
                evidence_obj = updates["evidence_json"]
            elif "evidence" in updates:
                evidence_obj = updates["evidence"]
            else:
                evidence_obj = conn.execute(
                    text("SELECT evidence_json FROM projects WHERE id = :pid"),
                    {"pid": project_id},
                ).scalar() or {}

            if evidence_obj is None or not isinstance(evidence_obj, dict):
                raise HTTPException(status_code=400, detail="Evidence payload must be a JSON object")

            evidence_obj = dict(evidence_obj)
            if "metrics" in updates:
                evidence_obj["metrics"] = updates["metrics"]
            if "feedback" in updates:
                evidence_obj["feedback"] = updates["feedback"]
            if "evaluation" in updates:
                evidence_obj["evaluation"] = updates["evaluation"]

            set_clauses.append("evidence_json = CAST(:evidence_json AS jsonb)")
            params["evidence_json"] = json.dumps(evidence_obj)

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid update fields provided")

        conn.execute(
            text(f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = :pid"),
            params,
        )

        updated = conn.execute(
            text(
                """
                SELECT id, display_name, user_role, evidence_json
                FROM projects
                WHERE id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first()

    return {
        "project_id": str(updated["id"]),
        "display_name": updated.get("display_name"),
        "user_role": updated.get("user_role"),
        "evidence_json": updated.get("evidence_json") or {},
    }

@app.get("/portfolio/{portfolio_id}/top-projects")
def top_projects(
    portfolio_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    """
    Returns a ranked summary for the top projects in a portfolio.
    Summary is local-only and derived from latest completed parser/local_ml for each project's latest snapshot (best effort).
    """
    engine = get_engine()
    auth = _resolve_auth_context(credentials, required=False)
    if auth:
        with engine.connect() as conn:
            _assert_portfolio_owned_by(conn, portfolio_id=portfolio_id, user_id=auth["user_id"])

    listing = list_projects(portfolio_id=portfolio_id, user_id=None, credentials=None)
    projects = listing.get("projects") or []

    # list_projects is already ordered according to user_config.ranking.
    ranked = projects[: int(limit)]

    summaries: List[Dict[str, Any]] = []
    with engine.connect() as conn:
        for p in ranked:
            pid = p["id"]
            latest_sid = ((p.get("latest_snapshot") or {}).get("id")) or None
            if not latest_sid:
                summaries.append(
                    {
                        "project_id": pid,
                        "name": p.get("name"),
                        "rank_score": p["metrics"]["rank_score"],
                        "summary": None,
                    }
                )
                continue

            parser = conn.execute(
                text(
                    """
                    SELECT output_json
                    FROM analyses
                    WHERE snapshot_id = :sid AND analysis_type = 'parser' AND status = 'complete'
                    ORDER BY completed_at DESC NULLS LAST, created_at DESC
                    LIMIT 1
                    """
                ),
                {"sid": latest_sid},
            ).scalar() or {}

            ml = conn.execute(
                text(
                    """
                    SELECT output_json
                    FROM analyses
                    WHERE snapshot_id = :sid AND analysis_type = 'local_ml' AND status = 'complete'
                    ORDER BY completed_at DESC NULLS LAST, created_at DESC
                    LIMIT 1
                    """
                ),
                {"sid": latest_sid},
            ).scalar() or {}

            top_lang = []
            try:
                top_lang = (parser.get("top_languages") or [])[:3]
            except Exception:
                top_lang = []

            top_skills = []
            try:
                top_skills = (ml.get("skills") or [])[:5]
            except Exception:
                top_skills = []

            lang_str = ", ".join([str(x.get("language")) for x in top_lang if isinstance(x, dict) and x.get("language")]) or None
            skills_str = ", ".join([str(x.get("skill")) for x in top_skills if isinstance(x, dict) and x.get("skill")]) or None

            summaries.append(
                {
                    "project_id": pid,
                    "name": p.get("name"),
                    "rank_score": p["metrics"]["rank_score"],
                    "features": {
                        "user_commits": p["metrics"].get("user_commits"),
                        "total_commits": p["metrics"].get("total_commits"),
                        "contributor_count": p["metrics"].get("contributor_count"),
                    },
                    "summary": {
                        "top_languages": lang_str,
                        "top_skills": skills_str,
                    },
                }
            )

    return {"portfolio_id": portfolio_id, "limit": int(limit), "top_projects": summaries}

@app.get("/portfolio/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    engine = get_engine()
    auth = _resolve_auth_context(credentials, required=False)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, user_id, name, created_at FROM portfolios WHERE id = :id"),
            {"id": portfolio_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        if auth and str(row["user_id"]) != auth["user_id"]:
            raise HTTPException(status_code=403, detail="Portfolio does not belong to the authenticated user")
    return dict(row)

class PortfolioGenerateIn(BaseModel):
    portfolio_id: str
    limit: int = Field(default=5, ge=1, le=50)
    persist: bool = True


class ResumeGenerateIn(BaseModel):
    project_id: str
    prefer_external_bullets: bool = True


@app.post("/resume/generate")
def generate_resume(payload: ResumeGenerateIn):
    """
    Creates a resume_items row (output artifact) for a given project.
    Returns the created resume_id and its stored content_json.
    """
    engine = get_engine()
    try:
        out = generate_resume_item(
            engine=engine,
            project_id=payload.project_id,
            prefer_external_bullets=bool(payload.prefer_external_bullets),
        )
        return out
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@app.post("/resume/{resume_id}/edit")
def edit_resume(resume_id: str, body: ResumeEditRequest):
    from src.db.session import get_engine
    from sqlalchemy import text
    import json

    engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT content_json FROM resume_items WHERE id = :id"),
            {"id": resume_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")

        raw = row["content_json"]
        content = json.loads(raw) if isinstance(raw, str) else raw

        if body.summary_text is not None:
            content["summary_text"] = body.summary_text

        if body.resume_bullets is not None:
            content["resume_bullets"] = body.resume_bullets

        conn.execute(
            text("UPDATE resume_items SET content_json = :c WHERE id = :id"),
            {
                "id": resume_id,
                "c": json.dumps(content),
            },
        )

    return {
        "resume_id": resume_id,   # ← THIS is what the test needs
        "content": content,
    }

@app.get("/resume/{resume_id}/pdf")
def download_resume_pdf(resume_id: str):
    engine = get_engine()
    try:
        # 1. Get the resume data
        item = get_resume_item(engine=engine, resume_id=resume_id)
        
        # 2. Fetch the user's config to get preferences
        from sqlalchemy import text
        with engine.connect() as conn:
            query = text("""
                SELECT uc.config_json 
                FROM user_config uc
                JOIN portfolios po ON uc.user_id = po.user_id
                JOIN projects pr ON po.id = pr.portfolio_id
                JOIN resume_items ri ON pr.id = ri.project_id
                WHERE ri.id = :rid
            """)
            result = conn.execute(query, {"rid": resume_id}).mappings().first()

            print(f"DEBUG: Found config for resume {resume_id}: {result is not None}")
            
            # Extract the filters if they exist, otherwise empty dict
            user_config = result["config_json"] if result else {}
            filters = user_config.get("resume_filters", {})

            print(f"DEBUG: Filters being sent to exporter: {filters}")

    except KeyError:
        raise HTTPException(status_code=404, detail="Resume item not found")

    # 3. Pass the filters into the exporter we just modified
    pdf_bytes = export_resume_item_pdf_bytes(item, filters=filters)
    
    filename = f"resume-{resume_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/resume/{resume_id}")
def get_resume(resume_id: str):
    """
    Retrieves a previously generated resume item by id.
    """
    engine = get_engine()
    try:
        return get_resume_item(engine=engine, resume_id=resume_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Resume item not found")


@app.post("/portfolio/generate")
def generate_portfolio(payload: PortfolioGenerateIn):
    """
    Generates top-ranked project summaries for a portfolio.
    If persist=true, creates portfolio_showcases rows (output artifacts) per summarized project.
    """
    engine = get_engine()
    try:
        out = generate_portfolio_top_summaries(
            engine=engine,
            portfolio_id=payload.portfolio_id,
            limit=int(payload.limit),
            persist=bool(payload.persist),
        )
        return out
    except KeyError:
        raise HTTPException(status_code=404, detail="Portfolio not found")

@app.post("/portfolio/{showcase_id}/edit")
def edit_portfolio_showcase(showcase_id: str, body: PortfolioEditRequest):
    engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT content_json FROM portfolio_showcases WHERE id = :id"),
            {"id": showcase_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Showcase not found")

        content = row["content_json"]

        if body.title is not None:
            content["title"] = body.title

        if body.summary_text is not None:
            content["summary_text"] = body.summary_text

        conn.execute(
            text(
                "UPDATE portfolio_showcases SET content_json = :c WHERE id = :id"
            ),
            {"id": showcase_id,"c": json.dumps(content),
            },
)


    return {"showcase_id": showcase_id, "content": content}

@app.get("/portfolio/{portfolio_id}/generated")
def get_generated_portfolio_artifacts(portfolio_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """
    Retrieves previously generated portfolio_showcases artifacts for the portfolio.
    """
    engine = get_engine()
    try:
        return list_portfolio_showcases(engine=engine, portfolio_id=portfolio_id, limit=int(limit))
    except KeyError:
        raise HTTPException(status_code=404, detail="Portfolio not found")


class IdentityRulesIn(BaseModel):
    match_emails: List[str] = Field(default_factory=list)
    match_names: List[str] = Field(default_factory=list)


class AutoLinkIdentityIn(BaseModel):
    portfolio_id: Optional[str] = None
    dry_run: bool = False
    persist_project_map: bool = True


def _dedup_str_list(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        s = str(x).strip()
        if not s:
            continue
        key = s.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


@app.post("/users/{user_id}/identity/rules")
def set_identity_rules(user_id: str, payload: IdentityRulesIn):
    """
    Convenience endpoint:
      - Writes identity.match_emails and identity.match_names into user_config.
    """
    engine = get_engine()
    with engine.begin() as conn:
        cfg = get_user_config(conn, user_id)
        ident = cfg.setdefault("identity", {})
        ident["match_emails"] = _dedup_str_list(payload.match_emails or [])
        ident["match_names"] = _dedup_str_list(payload.match_names or [])
        cfg = put_user_config(conn, user_id, cfg)
    return {"user_id": user_id, "identity": cfg.get("identity") or {}}


def _choose_user_contributor_for_project(
    conn,
    *,
    user_id: str,
    project_id: str,
) -> Tuple[Optional[str], str]:
    """
    Returns (chosen_contributor_id, reason).
    Uses:
      1) identity.project_contributor_map[project_id] if present
      2) match by identity.match_emails / identity.match_names against contributors on the project
         choosing highest-commits match.
    """
    match_emails, match_names, mapping = identity_rules_for_user(conn, user_id)

    mapped = (mapping or {}).get(str(project_id))
    if mapped:
        return str(mapped), "config.project_contributor_map"

    email_set = {str(e).strip().casefold() for e in (match_emails or []) if str(e).strip()}
    name_set = {str(n).strip().casefold() for n in (match_names or []) if str(n).strip()}
    if not email_set and not name_set:
        return None, "no_identity_rules"

    rows = conn.execute(
        text(
            """
            WITH contrib_commits AS (
              SELECT
                ce.contributor_id,
                COALESCE(SUM(ce.commit_count), 0) AS commits
              FROM contribution_events ce
              JOIN snapshots s ON s.id = ce.snapshot_id
              WHERE s.project_id = :pid
              GROUP BY ce.contributor_id
            )
            SELECT
              c.id AS contributor_id,
              c.canonical_name,
              c.email,
              COALESCE(cc.commits, 0) AS commits
            FROM project_contributors pc
            JOIN contributors c ON c.id = pc.contributor_id
            LEFT JOIN contrib_commits cc ON cc.contributor_id = pc.contributor_id
            WHERE pc.project_id = :pid
            """
        ),
        {"pid": project_id},
    ).mappings().all()

    candidates: List[Tuple[int, str]] = []
    for r in rows:
        cid = str(r["contributor_id"])
        commits = int(r.get("commits") or 0)
        nm_cf = str(r.get("canonical_name") or "").strip().casefold()
        em_cf = str(r.get("email") or "").strip().casefold()

        if em_cf and em_cf in email_set:
            candidates.append((commits, cid))
            continue
        if nm_cf and nm_cf in name_set:
            candidates.append((commits, cid))
            continue

    if not candidates:
        return None, "no_matches"

    candidates.sort(key=lambda t: (-int(t[0]), str(t[1])))
    return str(candidates[0][1]), "rule_match_best_commits"


def _apply_is_user_flag(conn, *, project_id: str, contributor_id: str, unset_others: bool = True) -> None:
    conn.execute(
        text(
            """
            INSERT INTO project_contributors (project_id, contributor_id, is_user)
            VALUES (:pid, :cid, FALSE)
            ON CONFLICT (project_id, contributor_id) DO NOTHING
            """
        ),
        {"pid": project_id, "cid": contributor_id},
    )
    if unset_others:
        conn.execute(
            text(
                """
                UPDATE project_contributors
                SET is_user = FALSE
                WHERE project_id = :pid AND contributor_id <> :cid
                """
            ),
            {"pid": project_id, "cid": contributor_id},
        )
    conn.execute(
        text(
            """
            UPDATE project_contributors
            SET is_user = TRUE
            WHERE project_id = :pid AND contributor_id = :cid
            """
        ),
        {"pid": project_id, "cid": contributor_id},
    )


@app.post("/users/{user_id}/identity/auto-link")
def auto_link_identity(user_id: str, payload: AutoLinkIdentityIn):
    engine = get_engine()
    with engine.begin() as conn:
        portfolio_ids: List[str] = []
        if payload.portfolio_id:
            owned = conn.execute(
                text("SELECT 1 FROM portfolios WHERE id = :pid AND user_id = :uid"),
                {"pid": payload.portfolio_id, "uid": user_id},
            ).scalar()
            if not owned:
                raise HTTPException(status_code=404, detail="Portfolio not found for user")
            portfolio_ids = [payload.portfolio_id]
        else:
            portfolio_ids = [
                str(x)
                for x in conn.execute(
                    text("SELECT id FROM portfolios WHERE user_id = :uid ORDER BY created_at ASC"),
                    {"uid": user_id},
                ).scalars().all()
            ]

        pids_uuid = [uuid.UUID(p) for p in portfolio_ids]

        stmt = text(
            """
            SELECT id
            FROM projects
            WHERE portfolio_id = ANY(:pids)
            ORDER BY created_at ASC
            """
        ).bindparams(bindparam("pids", type_=ARRAY(UUID(as_uuid=True))))

        projects = conn.execute(stmt, {"pids": pids_uuid}).scalars().all()
        projects = [str(p) for p in projects]

        results: List[Dict[str, Any]] = []
        for pid in projects:
            chosen, reason = _choose_user_contributor_for_project(conn, user_id=user_id, project_id=pid)
            if not chosen:
                results.append({"project_id": pid, "chosen_contributor_id": None, "applied": False, "reason": reason})
                continue

            if not payload.dry_run:
                _apply_is_user_flag(conn, project_id=pid, contributor_id=chosen, unset_others=True)
                if payload.persist_project_map:
                    set_project_user_contributor_mapping(conn, user_id, pid, chosen)

            results.append(
                {
                    "project_id": pid,
                    "chosen_contributor_id": chosen,
                    "applied": (not payload.dry_run),
                    "reason": reason,
                }
            )

    return {"user_id": user_id, "portfolio_ids": portfolio_ids, "dry_run": bool(payload.dry_run), "results": results}

@app.post("/projects/{project_id}/refresh-collaboration")
def refresh_project_collaboration(project_id: str):
    """
    Recomputes and persists projects.collaboration_type based on distinct contributors observed for the project.
    Useful after backfilling git_metrics or importing older DB state.
    """
    engine = get_engine()
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM projects WHERE id = :pid"), {"pid": project_id}).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Project not found")

        contributor_count = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT pc.contributor_id)
                    FROM project_contributors pc
                    WHERE pc.project_id = :pid
                    """
                ),
                {"pid": project_id},
            ).scalar_one()
        )

        ctype = "collaborative" if contributor_count > 1 else "individual"
        conn.execute(
            text("UPDATE projects SET collaboration_type = :ct WHERE id = :pid"),
            {"ct": ctype, "pid": project_id},
        )

    return {"project_id": project_id, "collaboration_type": ctype, "contributor_count": contributor_count}


@app.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: str):
    """
    Safe deletion:
      - Deletes snapshot and cascaded derived rows (analyses, snapshot_files, contribution_events).
      - Garbage-collects unreferenced file_blobs (shared blobs remain if referenced elsewhere).
    """
    engine = get_engine()
    try:
        return delete_snapshot_and_gc(engine, snapshot_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Snapshot not found")


@app.delete("/portfolio/showcases/{showcase_id}")
def delete_portfolio_showcase(showcase_id: str):
    """
    Deletes a previously generated portfolio_showcases artifact.
    If it had a thumbnail blob, GC it only if unreferenced elsewhere.
    """
    engine = get_engine()
    try:
        return delete_portfolio_showcase_and_gc(engine, showcase_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Showcase not found")


@app.delete("/resume/{resume_id}")
def delete_resume(resume_id: str):
    """
    Deletes a previously generated resume_items artifact.
    """
    engine = get_engine()
    try:
        return delete_resume_item(engine, resume_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Resume item not found")


@app.delete("/analyses/{analysis_id}")
def delete_analysis_by_id(analysis_id: str):
    """
    Deletes a previously generated analysis/insight by analysis id.
    """
    engine = get_engine()
    try:
        return delete_analysis(engine, analysis_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Analysis not found")


@app.post("/extract-commits/")
async def extract_commits(file: UploadFile):
    # Save uploaded zip to a temp file
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.write(await file.read())
    tmp_zip.close()

    # Extract zip to temp dir
    tmp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp_zip.name, 'r') as zf:
        zf.extractall(tmp_dir)

    # Find the git repo
    try:
        repo = find_git_repo(tmp_dir)
    except InvalidGitRepositoryError:
        return {"error": "Uploaded zip is not a valid git repo"}

    # Extract commits
    commits = [{"message": c.message, "author": c.author.name, "hexsha": c.hexsha} for c in repo.iter_commits()]
    return {"commits": commits}


@app.post("/extract-commit-counts/")
async def extract_commit_counts(file: UploadFile):
    # Save uploaded zip to a temp file
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.write(await file.read())
    tmp_zip.close()

    # Extract zip to temp dir
    tmp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp_zip.name, 'r') as zf:
        zf.extractall(tmp_dir)

    # Find the git repo
    try:
        repo = find_git_repo(tmp_dir)
    except InvalidGitRepositoryError:
        return {"error": "Uploaded zip is not a valid git repo"}

    # Count commits per author
    commit_counts = Counter()
    for c in repo.iter_commits():
        commit_counts[c.author.name] += 1

    # Sort by number of commits descending
    sorted_counts = dict(sorted(commit_counts.items(), key=lambda x: x[1], reverse=True))

    return {"commit_counts": sorted_counts}


@app.post("/give-users-roles/")
async def extract_commits(file: UploadFile):
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.write(await file.read())
    tmp_zip.close()

    tmp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp_zip.name, 'r') as zf:
        zf.extractall(tmp_dir)

    try:
        repo = find_git_repo(tmp_dir)
    except InvalidGitRepositoryError:
        return {"error": "Uploaded zip is not a valid git repo"}

    commits = list(repo.iter_commits())
    commit_counts = Counter(c.author.name for c in commits)
    
    roles = assign_roles(dict(commit_counts))

    return {
        "commit_counts": dict(commit_counts),
        "roles": roles
    }


@app.get("/portfolio/{portfolio_id}/projects/chronological")
def list_portfolio_projects_chronological(
    portfolio_id: str,
    direction: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=200, ge=1, le=2000),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    """
    Portfolio-level chronological list of projects.
    This is distinct from /projects (which returns ranked ordering).
    """
    engine = get_engine()
    auth = _resolve_auth_context(credentials, required=False)
    with engine.connect() as conn:
        if auth:
            _assert_portfolio_owned_by(conn, portfolio_id=portfolio_id, user_id=auth["user_id"])

        owned = conn.execute(text("SELECT 1 FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
        if not owned:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        portfolio_user_id = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        user_cfg = get_user_config(conn, str(portfolio_user_id)) if portfolio_user_id else {}
        chronology_cfg = (user_cfg or {}).get("chronology") or {}

        portfolio_user_id = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        user_cfg = get_user_config(conn, str(portfolio_user_id)) if portfolio_user_id else {}
        chronology_cfg = (user_cfg or {}).get("chronology") or {}

        rows = conn.execute(
            text(
                """
                SELECT
                  id,
                  name,
                  project_type,
                  collaboration_type,
                  user_role,
                  created_at
                FROM projects
                WHERE portfolio_id = :pid
                """
            ),
            {"pid": portfolio_id},
        ).mappings().all()

    projects = [dict(r) for r in rows]

    project_order = chronology_cfg.get("project_order") or []
    if not isinstance(project_order, list):
        project_order = []
    project_order = [str(x).strip() for x in project_order if str(x).strip()]
    order_index = {pid: i for i, pid in enumerate(project_order)}

    project_dates = chronology_cfg.get("project_dates") or {}
    if not isinstance(project_dates, dict):
        project_dates = {}
    project_dates = {str(k): str(v) for k, v in project_dates.items() if str(k).strip() and str(v).strip()}

    # If project_order is provided, it has precedence and can override chronology.
    if project_order:
        by_id = {str(p.get("id")): p for p in projects}
        ordered = [by_id[pid] for pid in project_order if pid in by_id]
        remaining = [p for p in projects if str(p.get("id")) not in order_index]
        remaining.sort(key=lambda p: (str(p.get("created_at") or ""), str(p.get("id") or "")), reverse=(direction == "desc"))

        if direction == "desc":
            ordered = list(reversed(ordered))

        final = ordered + remaining
    else:
        # Otherwise, use per-project date overrides (if any) to produce corrected chronology.
        def sort_key(p: Dict[str, Any]):
            pid = str(p.get("id") or "")
            ts = project_dates.get(pid) or p.get("created_at")
            return (str(ts or ""), str(pid))

        final = sorted(projects, key=sort_key, reverse=(direction == "desc"))

    # Surface the corrected sort key for consumers.
    for p in final:
        pid = str(p.get("id") or "")
        p["chronology"] = {
            "sort_ts": project_dates.get(pid) or (p.get("created_at").isoformat() if hasattr(p.get("created_at"), "isoformat") else str(p.get("created_at") or "")),
            "overridden": bool(pid in project_dates or pid in order_index),
        }

    final = final[: int(limit)]

    return {
        "portfolio_id": portfolio_id,
        "direction": direction,
        "limit": int(limit),
        "projects": final,
    }


@app.get("/portfolio/{portfolio_id}/skills/chronological")
def list_portfolio_skills_chronological(
    portfolio_id: str,
    direction: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=500, ge=1, le=5000),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    """
    Portfolio-level chronological list of skills exercised.

    Derivation:
      - Read completed local_ml analyses for snapshots in the portfolio.
      - From output_json.skills[*].first_seen_ts (preferred), produce skill events with:
          (skill, first_seen_ts, project_id, snapshot_id, analysis_id, max_prob, hits)
      - If first_seen_ts is missing, fall back to snapshot.ingested_at.
    This aligns with the existing local_ml output schema. :contentReference[oaicite:2]{index=2}
    """
    engine = get_engine()
    auth = _resolve_auth_context(credentials, required=False)

    with engine.connect() as conn:
        if auth:
            _assert_portfolio_owned_by(conn, portfolio_id=portfolio_id, user_id=auth["user_id"])

        owned = conn.execute(text("SELECT 1 FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
        if not owned:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        portfolio_user_id = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        user_cfg = get_user_config(conn, str(portfolio_user_id)) if portfolio_user_id else {}
        chronology_cfg = (user_cfg or {}).get("chronology") or {}

        rows = conn.execute(
            text(
                """
                SELECT
                  a.id AS analysis_id,
                  a.snapshot_id,
                  a.output_json,
                  a.completed_at,
                  s.ingested_at,
                  prj.id AS project_id,
                  prj.name AS project_name
                FROM analyses a
                JOIN snapshots s ON s.id = a.snapshot_id
                JOIN projects prj ON prj.id = s.project_id
                WHERE prj.portfolio_id = :pid
                  AND a.analysis_type = 'local_ml'
                  AND a.status = 'complete'
                ORDER BY COALESCE(a.completed_at, s.ingested_at) ASC, a.created_at ASC
                """
            ),
            {"pid": portfolio_id},
        ).mappings().all()

    events = []
    for r in rows:
        out = r.get("output_json") or {}
        skills = out.get("skills") if isinstance(out, dict) else None
        if not isinstance(skills, list):
            continue

        for srow in skills:
            if not isinstance(srow, dict):
                continue
            skill = srow.get("skill")
            if not skill:
                continue

            ts = srow.get("first_seen_ts") or None
            # Fall back if model did not emit first_seen_ts.
            if not ts:
                fallback = r.get("ingested_at") or r.get("completed_at")
                ts = fallback.isoformat() if fallback is not None else None

            events.append(
                {
                    "skill": str(skill),
                    "first_seen_ts": ts,
                    "project_id": str(r.get("project_id")),
                    "project_name": r.get("project_name"),
                    "snapshot_id": str(r.get("snapshot_id")),
                    "analysis_id": str(r.get("analysis_id")),
                    "max_prob": srow.get("max_prob"),
                    "hits": srow.get("hits"),
                }
            )

    # Sort in-process to apply direction and ensure stable ordering.
    # Apply overrides and (optional) explicit skill ordering.
    skill_first_seen = chronology_cfg.get("skill_first_seen") or {}
    if not isinstance(skill_first_seen, dict):
        skill_first_seen = {}
    skill_first_seen_cf = {str(k).casefold(): str(v) for k, v in skill_first_seen.items() if str(k).strip() and str(v).strip()}

    skill_order = chronology_cfg.get("skill_order") or []
    if not isinstance(skill_order, list):
        skill_order = []
    skill_order = [str(x).strip() for x in skill_order if str(x).strip()]
    skill_order_idx = {s.casefold(): i for i, s in enumerate(skill_order)}

    for e in events:
        nm = str(e.get("skill") or "")
        ov = skill_first_seen_cf.get(nm.casefold())
        if ov:
            e["first_seen_ts"] = ov
            e["overridden"] = True
        if skill_order:
            e["skill_order_index"] = skill_order_idx.get(nm.casefold())

    def _k(e):
        idx = e.get("skill_order_index")
        idx_key = (0, int(idx)) if idx is not None else (1, 0)
        t = e.get("first_seen_ts") or ""
        return (idx_key, str(t), e.get("skill") or "", e.get("project_id") or "", e.get("snapshot_id") or "")

    events.sort(key=_k, reverse=(direction == "desc"))
    events = events[: int(limit)]

    return {
        "portfolio_id": portfolio_id,
        "direction": direction,
        "limit": int(limit),
        "skill_events": events,
    }


@app.put("/projects/{project_id}/image")
async def set_project_image(
    project_id: PyUUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Early FK check
    exists = db.execute(
        text("SELECT 1 FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Read file
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # 3. Hash
    sha256 = hashlib.sha256(data).hexdigest()

    # 4. Ensure upload directory exists
    UPLOAD_DIR = "uploads/project_images"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 5) Infer mime + build safe stored path
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower() or ".png"

    stored_path = os.path.join(
        UPLOAD_DIR,
        f"{sha256}{ext}",
    )
    stored_path = stored_path[:1024]  # DB safety

    # 6) Upsert file_blobs
    blob = (
        db.query(FileBlob)
        .filter(FileBlob.sha256 == sha256)
        .one_or_none()
    )

    if blob is None:
        # Write file to disk once
        with open(stored_path, "wb") as f:
            f.write(data)

        blob = FileBlob(
            sha256=sha256,
            size_bytes=len(data),
            mime_type=file.content_type,
            stored_path=stored_path,
        )
        db.add(blob)

    # 7) Create/update portfolio showcase
    showcase = (
        db.query(PortfolioShowcase)
        .filter(PortfolioShowcase.project_id == project_id)
        .one_or_none()
    )

    if showcase is None:
        showcase = PortfolioShowcase(
            project_id=project_id,
            thumbnail_blob_sha256=sha256,
        )
        db.add(showcase)
    else:
        showcase.thumbnail_blob_sha256 = sha256

    # 8) Commit once
    db.commit()

    return {
        "project_id": str(project_id),
        "thumbnail_blob_sha256": sha256,
        "stored_path": stored_path,
    }




@app.delete("/projects/{project_id}/image")
def delete_project_image(project_id: str):
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, thumbnail_blob_sha256
                FROM portfolio_showcases
                WHERE project_id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first()

        if not row or not row["thumbnail_blob_sha256"]:
            raise HTTPException(status_code=404, detail="Project image not found")

        conn.execute(
            text(
                """
                UPDATE portfolio_showcases
                SET thumbnail_blob_sha256 = NULL,
                    updated_at = NOW()
                WHERE id = :sid
                """
            ),
            {"sid": row["id"]},
        )

    return {"project_id": project_id, "deleted": True}


@app.put("/__debug/echo-upload")
async def echo_upload(file: UploadFile = File(...)):
    data = await file.read()
    import hashlib
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
