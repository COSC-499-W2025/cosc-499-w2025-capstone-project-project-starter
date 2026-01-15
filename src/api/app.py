from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from fastapi.responses import Response
from src.db.session import get_engine
from src.api.ingest import ingest_zip_to_db, save_upload_to_temp
from src.api.report import build_project_report
from src.db.consents import get_snapshot_owner_user_id, is_external_services_allowed

from src.db.user_config import (
    get_user_config,
    put_user_config,
    merge_user_config,
    identity_rules_for_user,
    resolve_project_owner_user_id,
    set_project_user_contributor_mapping,
    clear_project_user_contributor_mapping,
)

from src.api.pdf_exporter import export_resume_item_pdf_bytes

from src.api.generation import (
    generate_portfolio_top_summaries,
    generate_resume_item,
    list_portfolio_showcases,
    get_resume_item,
)

app = FastAPI(title="Artifact Miner API", version="0.1.0")


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


def _rank_score(user_commits: int, total_commits: int) -> Optional[float]:
    # Deterministic and transparent. Only meaningful if user_commits > 0.
    if user_commits <= 0:
        return None
    other = max(0, int(total_commits) - int(user_commits))
    return float(int(user_commits)) + 0.10 * float(other)


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
):
    """
    Lists projects with derived ranking metrics.
    Requires either portfolio_id or user_id.
    If user_id is provided, uses the user's default portfolio (name='default') if it exists.
    """
    engine = get_engine()
    with engine.connect() as conn:
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

    out = []
    for r in rows:
        total = int(r["total_commits"] or 0)
        userc = int(r["user_commits"] or 0)
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
                    "user_commits": userc if userc > 0 else None,
                    "contributor_count": int(r["contributor_count"] or 0),
                    "rank_score": _rank_score(userc, total),
                },
                "latest_snapshot": {
                    "id": str(r["latest_snapshot_id"]) if r.get("latest_snapshot_id") else None,
                    "ingested_at": r.get("latest_ingested_at"),
                },
            }
        )

    # Sort with rank_score desc NULLS LAST, then created_at asc for stability.
    out.sort(
        key=lambda x: (
            -1 if x["metrics"]["rank_score"] is None else 0,
            0.0 if x["metrics"]["rank_score"] is None else -float(x["metrics"]["rank_score"]),
            str(x["created_at"] or ""),
        )
    )

    return {"portfolio_id": str(portfolio_id), "projects": out}


@app.get("/portfolio/{portfolio_id}/top-projects")
def top_projects(portfolio_id: str, limit: int = Query(default=5, ge=1, le=50)):
    """
    Returns a ranked summary for the top projects in a portfolio.
    Summary is local-only and derived from latest completed parser/local_ml for each project's latest snapshot (best effort).
    """
    engine = get_engine()
    listing = list_projects(portfolio_id=portfolio_id, user_id=None)
    projects = listing.get("projects") or []

    # Keep only those with computed rank_score.
    ranked = [p for p in projects if (p.get("metrics") or {}).get("rank_score") is not None]
    ranked.sort(key=lambda p: float(p["metrics"]["rank_score"]), reverse=True)
    ranked = ranked[: int(limit)]

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

@app.get("/resume/{resume_id}/pdf")
def download_resume_pdf(resume_id: str):
    engine = get_engine()
    try:
        item = get_resume_item(engine=engine, resume_id=resume_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Resume item not found")

    pdf_bytes = export_resume_item_pdf_bytes(item)
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