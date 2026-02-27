from __future__ import annotations

import json
import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.db.user_config import get_user_config
from src.api.ranking import compute_rank_score, normalize_ranking_config, sort_projects

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_latest_snapshot_id(conn, project_id: str) -> Optional[str]:
    return conn.execute(
        text(
            """
            SELECT id
            FROM snapshots
            WHERE project_id = :pid
            ORDER BY ingested_at DESC
            LIMIT 1
            """
        ),
        {"pid": project_id},
    ).scalar()


def _fetch_latest_completed_analysis_output(conn, snapshot_id: str, analysis_type: str) -> Dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT output_json
            FROM analyses
            WHERE snapshot_id = :sid AND analysis_type = :atype AND status = 'complete'
            ORDER BY completed_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        ),
        {"sid": snapshot_id, "atype": analysis_type},
    ).mappings().first()
    if not row:
        return {}
    out = row.get("output_json") or {}
    return out if isinstance(out, dict) else {}


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)].rstrip() + "…"


def _comma_list(xs: List[str], max_items: int) -> Optional[str]:
    clean = [str(x).strip() for x in (xs or []) if str(x).strip()]
    if not clean:
        return None
    return ", ".join(clean[:max_items])


def _derive_project_summary_text(
    *,
    project_name: str,
    collab_type: Optional[str],
    top_languages: List[str],
    frameworks: List[str],
    top_skills: List[str],
    user_commits: Optional[int],
    total_commits: Optional[int],
    contributor_count: Optional[int],
) -> str:
    parts: List[str] = []

    langs = _comma_list(top_languages, 3)
    frws = _comma_list(frameworks, 3)
    skills = _comma_list(top_skills, 6)

    tech_bits: List[str] = []
    if langs:
        tech_bits.append(langs)
    if frws:
        tech_bits.append(frws)
    if tech_bits:
        parts.append(f"Tech: {', '.join(tech_bits)}.")

    if skills:
        parts.append(f"Skills: {skills}.")

    # Only mention git-derived activity when it is non-zero.
    # A zip upload that is not a git repo will yield 0/0 aggregates; emitting
    # "0 commits" is unhelpful.
    if (
        total_commits is not None
        and contributor_count is not None
        and int(total_commits) > 0
        and int(contributor_count) > 0
    ):
        if user_commits is not None and user_commits > 0:
            parts.append(
                f"Contributions: {user_commits} of {total_commits} commits; {contributor_count} contributor(s); {collab_type or 'unknown'}."
            )
        else:
            parts.append(f"Activity: {total_commits} commits; {contributor_count} contributor(s); {collab_type or 'unknown'}.")

    if not parts:
        return _truncate(f"{project_name}: project summary unavailable (insufficient completed analyses).", 240)

    return _truncate(f"{project_name}. " + " ".join(parts), 320)


def _local_resume_bullets(
    *,
    project_name: str,
    top_languages: List[str],
    frameworks: List[str],
    top_skills: List[str],
    user_commits: Optional[int],
    total_commits: Optional[int],
    contributor_count: Optional[int],
    collab_type: Optional[str],
    highlight_skills: Optional[List[str]] = None,
) -> List[str]:
    langs = _comma_list(top_languages, 2)
    frws = _comma_list(frameworks, 2)
    skills = _comma_list(top_skills, 4)

    tech = _comma_list([x for x in [langs, frws] if x], 4)

    b1 = f"Built and iterated on {project_name}"
    if tech:
        b1 += f" using {tech}"
    if skills:
        b1 += f", applying {skills}"
    b1 += "."

    has_git_activity = (
        total_commits is not None
        and contributor_count is not None
        and int(total_commits) > 0
        and int(contributor_count) > 0
    )

    if has_git_activity:
        if user_commits is not None and user_commits > 0:
            b2 = f"Delivered {user_commits} of {total_commits} commits in a {collab_type or 'collaborative'} setting with {contributor_count} contributor(s)."
        else:
            b2 = f"Worked across {total_commits} commits with {contributor_count} contributor(s); collaboration type: {collab_type or 'unknown'}."
    else:
        b2 = "Coordinated work across multiple iterations and snapshots, maintaining a repeatable analysis pipeline."

    # Prefer a highlighted skill if it is present in detected skills.
    focus_skill = None
    hi = [str(x).strip() for x in (highlight_skills or []) if str(x).strip()]
    hi_cf = {x.casefold() for x in hi}
    for s in (top_skills or []):
        if str(s).casefold() in hi_cf:
            focus_skill = str(s)
            break
    if not focus_skill:
        for s in (top_skills or []):
            candidate = str(s).strip()
            if candidate:
                focus_skill = candidate
                break
    if focus_skill:
        if has_git_activity:
            b3 = f"Demonstrated proficiency in {focus_skill} through measurable repository activity and structured project outputs."
        else:
            b3 = f"Demonstrated proficiency in {focus_skill} through structured project outputs and iterative development."
    else:
        b3 = "Translated technical work into clear, resume-ready outcomes aligned with project goals."

    return [_truncate(b1, 180), _truncate(b2, 180), _truncate(b3, 180)]


def _external_resume_bullets(external_llm_out: Dict[str, Any]) -> Optional[List[str]]:
    """
    Expects output shape from worker.llm.run_external_llm_analysis:
      {"result": {"resume_bullets": [...]}} (best case)
    """
    try:
        res = external_llm_out.get("result")
        if not isinstance(res, dict):
            return None
        bullets = res.get("resume_bullets")
        if not isinstance(bullets, list):
            return None
        clean = [str(x).strip() for x in bullets if str(x).strip()]
        if len(clean) < 3:
            return None
        return [_truncate(clean[0], 180), _truncate(clean[1], 180), _truncate(clean[2], 180)]
    except Exception:
        logger.warning("Failed to parse external resume bullets payload", exc_info=True)
        return None


def _ranked_projects_for_portfolio(conn, portfolio_id: str) -> List[Dict[str, Any]]:
    """
    Ranking rule:
      - Default behavior matches Milestone 1.
      - Milestone 2 adds user_config.ranking (auto|weighted|manual) for re-ranking.
    """
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
              p.id,
              p.name,
              p.project_type,
              p.collaboration_type,
              p.user_role,
              p.created_at,
              COALESCE(t.total_commits, 0) AS total_commits,
              COALESCE(ut.user_commits, 0) AS user_commits,
              COALESCE(t.contributor_count, 0) AS contributor_count,
              l.latest_snapshot_id
            FROM projects p
            LEFT JOIN totals t ON t.project_id = p.id
            LEFT JOIN user_totals ut ON ut.project_id = p.id
            LEFT JOIN latest l ON l.project_id = p.id
            WHERE p.portfolio_id = :pf
            ORDER BY p.created_at ASC
            """
        ),
        {"pf": portfolio_id},
    ).mappings().all()

    # Load ranks
    uid = conn.execute(text("SELECT user_id FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
    user_cfg = get_user_config(conn, str(uid)) if uid else {}
    ranking_cfg = normalize_ranking_config((user_cfg or {}).get("ranking") or {})

    out: List[Dict[str, Any]] = []
    for r in rows:
        total = int(r["total_commits"] or 0)
        userc_raw = int(r["user_commits"] or 0)
        userc = userc_raw if userc_raw > 0 else None

        rank_score = compute_rank_score(
            user_commits=userc,
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
                    "user_commits": userc,
                    "contributor_count": int(r["contributor_count"] or 0),
                    "rank_score": rank_score,
                },
                "latest_snapshot_id": str(r["latest_snapshot_id"]) if r.get("latest_snapshot_id") else None,
            }
        )

    return sort_projects(out, ranking_cfg)


def _merge_highlighted_skills(detected: List[str], highlighted: List[str], limit: int) -> List[str]:
    det = [str(x).strip() for x in (detected or []) if str(x).strip()]
    hi = [str(x).strip() for x in (highlighted or []) if str(x).strip()]

    det_cf = {x.casefold() for x in det}
    out: List[str] = []

    # Add highlighted skills that are actually present in the project.
    for s in hi:
        if s.casefold() in det_cf and s not in out:
            out.append(s)

    for s in det:
        if s not in out:
            out.append(s)

    return out[: max(0, int(limit))]


def generate_portfolio_top_summaries(
    *,
    engine: Engine,
    portfolio_id: str,
    limit: int,
    persist: bool,
) -> Dict[str, Any]:
    generated_at = _utcnow_iso()
    logger.info(
        "Generating portfolio top summaries for portfolio %s (limit=%d, persist=%s)",
        portfolio_id,
        int(limit),
        bool(persist),
    )

    with engine.begin() as conn:
        pf_ok = conn.execute(text("SELECT 1 FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
        if not pf_ok:
            raise KeyError("Portfolio not found")

        uid = conn.execute(text("SELECT user_id FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
        user_cfg = get_user_config(conn, str(uid)) if uid else {}
        highlight_skills = ((user_cfg or {}).get("highlights") or {}).get("skills") or []
        selected_ids = ((user_cfg or {}).get("showcase") or {}).get("selected_project_ids") or []

        ranked_all = _ranked_projects_for_portfolio(conn, portfolio_id)
        if isinstance(selected_ids, list) and any(str(x).strip() for x in selected_ids):
            selected_ids = [str(x).strip() for x in selected_ids if str(x).strip()]
            by_id = {str(p["id"]): p for p in ranked_all}
            chosen = [by_id[pid] for pid in selected_ids if pid in by_id]
            ranked = chosen[: int(limit)]
        else:
            ranked = ranked_all[: int(limit)]

        top_projects: List[Dict[str, Any]] = []
        showcase_ids: List[str] = []

        for p in ranked:
            pid = p["id"]
            sid = p.get("latest_snapshot_id") or _fetch_latest_snapshot_id(conn, pid)
            parser_out = _fetch_latest_completed_analysis_output(conn, sid, "parser") if sid else {}
            ml_out = _fetch_latest_completed_analysis_output(conn, sid, "local_ml") if sid else {}
            git_out = _fetch_latest_completed_analysis_output(conn, sid, "git_metrics") if sid else {}

            top_languages = []
            try:
                top_languages = [str(x.get("language")) for x in (parser_out.get("top_languages") or []) if isinstance(x, dict) and x.get("language")]
            except Exception:
                top_languages = []

            frameworks = []
            try:
                frameworks = [str(x) for x in (parser_out.get("frameworks") or []) if str(x).strip()]
            except Exception:
                frameworks = []

            detected_skills = []
            try:
                detected_skills = [
                    str(x.get("skill"))
                    for x in (ml_out.get("skills") or [])
                    if isinstance(x, dict) and x.get("skill")
                ]
            except Exception:
                detected_skills = []

            top_skills = _merge_highlighted_skills(detected_skills, highlight_skills, limit=10)

            metrics = p.get("metrics") or {}
            summary_text = _derive_project_summary_text(
                project_name=p.get("name") or pid,
                collab_type=p.get("collaboration_type"),
                top_languages=top_languages,
                frameworks=frameworks,
                top_skills=top_skills,
                user_commits=metrics.get("user_commits"),
                total_commits=metrics.get("total_commits"),
                contributor_count=metrics.get("contributor_count"),
            )

            # Prefer external bullets if already available; otherwise local bullets.
            ext_out = _fetch_latest_completed_analysis_output(conn, sid, "external_llm") if sid else {}
            bullets = _external_resume_bullets(ext_out) or _local_resume_bullets(
                project_name=p.get("name") or pid,
                top_languages=top_languages,
                frameworks=frameworks,
                top_skills=top_skills,
                user_commits=metrics.get("user_commits"),
                total_commits=metrics.get("total_commits"),
                contributor_count=metrics.get("contributor_count"),
                collab_type=p.get("collaboration_type"),
                highlight_skills=highlight_skills,
            )

            artifact = {
                "type": "portfolio_project_summary",
                "generated_at": generated_at,
                "project_id": pid,
                "project_name": p.get("name"),
                "rank_score": metrics.get("rank_score"),
                "metrics": metrics,
                "latest_snapshot_id": sid,
                "summary_text": summary_text,
                "resume_bullets": bullets,
                "signals": {
                    "parser": {"generated_at": parser_out.get("generated_at"), "top_languages": parser_out.get("top_languages"), "activity_counts": parser_out.get("activity_counts")},
                    "local_ml": {"generated_at": ml_out.get("generated_at"), "threshold": ml_out.get("threshold"), "top_skills": (ml_out.get("skills") or [])[:15]},
                    "git_metrics": {"generated_at": git_out.get("generated_at"), "git_repos_found": git_out.get("git_repos_found"), "repo_summaries": (git_out.get("repo_summaries") or [])[:5]},
                },
            }

            showcase_id = None
            if persist:
                payload = json.dumps(artifact, default=str)
                
                # ATOMIC UPSERT: Handles the race condition safely
                showcase_id = conn.execute(
                    text(
                        """
                        INSERT INTO portfolio_showcases (project_id, thumbnail_blob_sha256, content_json, updated_at)
                        VALUES (:pid, NULL, CAST(:cj AS jsonb), NOW())
                        ON CONFLICT (project_id) DO UPDATE
                        SET content_json = EXCLUDED.content_json,
                            updated_at = EXCLUDED.updated_at
                        RETURNING id
                        """
                    ),
                    {"pid": pid, "cj": payload},
                ).scalar_one()
                
                showcase_ids.append(str(showcase_id))

            top_projects.append(
                {
                    "project_id": pid,
                    "project_name": p.get("name"),
                    "rank_score": metrics.get("rank_score"),
                    "summary_text": summary_text,
                    "resume_bullets": bullets,
                    "latest_snapshot_id": sid,
                    "showcase_id": str(showcase_id) if showcase_id else None,
                }
            )

    result = {
        "portfolio_id": portfolio_id,
        "generated_at": generated_at,
        "limit": int(limit),
        "persisted": bool(persist),
        "showcase_ids": showcase_ids,
        "top_projects": top_projects,
    }
    logger.info(
        "Generated portfolio summaries for portfolio %s (projects=%d persisted_showcases=%d)",
        portfolio_id,
        len(top_projects),
        len(showcase_ids),
    )
    return result


def generate_resume_item(
    *,
    engine: Engine,
    project_id: str,
    prefer_external_bullets: bool,
) -> Dict[str, Any]:
    generated_at = _utcnow_iso()
    logger.info(
        "Generating resume item for project %s (prefer_external_bullets=%s)",
        project_id,
        bool(prefer_external_bullets),
    )

    with engine.begin() as conn:
        proj = conn.execute(
            text("SELECT id, COALESCE(display_name, name) as name, portfolio_id, collaboration_type, user_role FROM projects WHERE id = :pid"),
            {"pid": project_id},
        ).mappings().first()
        if not proj:
            raise KeyError("Project not found")

        uid = conn.execute(
            text("SELECT user_id FROM portfolios WHERE id = :pid"),
            {"pid": str(proj.get("portfolio_id"))},
        ).scalar()
        user_cfg = get_user_config(conn, str(uid)) if uid else {}
        highlight_skills = ((user_cfg or {}).get("highlights") or {}).get("skills") or []

        sid = _fetch_latest_snapshot_id(conn, project_id)
        parser_out = _fetch_latest_completed_analysis_output(conn, sid, "parser") if sid else {}
        ml_out = _fetch_latest_completed_analysis_output(conn, sid, "local_ml") if sid else {}
        git_out = _fetch_latest_completed_analysis_output(conn, sid, "git_metrics") if sid else {}

        # Pull aggregate contribution totals for this project (cross-snapshot)
        totals = conn.execute(
            text(
                """
                SELECT
                  COALESCE(SUM(ce.commit_count), 0) AS total_commits,
                  COUNT(DISTINCT ce.contributor_id) AS contributor_count
                FROM contribution_events ce
                JOIN snapshots s ON s.id = ce.snapshot_id
                WHERE s.project_id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first() or {"total_commits": 0, "contributor_count": 0}

        user_commits = conn.execute(
            text(
                """
                SELECT COALESCE(SUM(ce.commit_count), 0) AS user_commits
                FROM contribution_events ce
                JOIN snapshots s ON s.id = ce.snapshot_id
                JOIN project_contributors pc
                  ON pc.project_id = s.project_id
                 AND pc.contributor_id = ce.contributor_id
                 AND pc.is_user = TRUE
                WHERE s.project_id = :pid
                """
            ),
            {"pid": project_id},
        ).scalar()
        user_commits_val = int(user_commits or 0)
        user_commits_out = user_commits_val if user_commits is not None and user_commits_val > 0 else None

        top_languages = []
        try:
            top_languages = [str(x.get("language")) for x in (parser_out.get("top_languages") or []) if isinstance(x, dict) and x.get("language")]
        except Exception:
            top_languages = []

        frameworks = []
        try:
            frameworks = [str(x) for x in (parser_out.get("frameworks") or []) if str(x).strip()]
        except Exception:
            frameworks = []

        detected_skills = []
        try:
            detected_skills = [
                str(x.get("skill"))
                for x in (ml_out.get("skills") or [])
                if isinstance(x, dict) and x.get("skill")
            ]
        except Exception:
            detected_skills = []

        top_skills = _merge_highlighted_skills(detected_skills, highlight_skills, limit=15)

        summary_text = _derive_project_summary_text(
            project_name=str(proj.get("name") or project_id),
            collab_type=str(proj.get("collaboration_type") or ""),
            top_languages=top_languages,
            frameworks=frameworks,
            top_skills=top_skills,
            user_commits=user_commits_out,
            total_commits=int(totals.get("total_commits") or 0),
            contributor_count=int(totals.get("contributor_count") or 0),
        )

        bullets: List[str]
        if prefer_external_bullets and sid:
            ext_out = _fetch_latest_completed_analysis_output(conn, sid, "external_llm")
            bullets = _external_resume_bullets(ext_out) or _local_resume_bullets(
                project_name=str(proj.get("name") or project_id),
                top_languages=top_languages,
                frameworks=frameworks,
                top_skills=top_skills,
                user_commits=user_commits_out,
                total_commits=int(totals.get("total_commits") or 0),
                contributor_count=int(totals.get("contributor_count") or 0),
                collab_type=str(proj.get("collaboration_type") or ""),
                highlight_skills=highlight_skills,
            )
        else:
            bullets = _local_resume_bullets(
                project_name=str(proj.get("name") or project_id),
                top_languages=top_languages,
                frameworks=frameworks,
                top_skills=top_skills,
                user_commits=user_commits_out,
                total_commits=int(totals.get("total_commits") or 0),
                contributor_count=int(totals.get("contributor_count") or 0),
                collab_type=str(proj.get("collaboration_type") or ""),
                highlight_skills=highlight_skills,
            )

        # --- FIXED THUMBNAIL HANDLING ---
        thumb = conn.execute(
            text("""
                SELECT fb.sha256, fb.mime_type, fb.stored_path
                FROM portfolio_showcases ps
                JOIN file_blobs fb
                  ON fb.sha256 = ps.thumbnail_blob_sha256
                WHERE ps.project_id = :pid
                LIMIT 1
            """),
            {"pid": str(proj["id"])},
        ).mappings().first()

        thumbnail_blob_json = None
        thumbnail_blob_sha256 = None

        if thumb and thumb.get("stored_path"):
            try:
                with open(thumb["stored_path"], "rb") as f:
                    file_bytes = f.read()
                    # ENCODE FOR JSON
                    thumbnail_blob_json = {
                        "data_base64": base64.b64encode(file_bytes).decode("ascii"),
                        "mime_type": thumb.get("mime_type"),
                    }
                    thumbnail_blob_sha256 = thumb.get("sha256")
            except Exception:
                logger.warning(
                    "Failed to load thumbnail blob for project %s",
                    proj.get("id"),
                    exc_info=True,
                )



        artifact = {
            "type": "resume_item",
            "generated_at": generated_at,
            "project": {
                "id": str(proj["id"]),
                "portfolio_id": str(proj["portfolio_id"]),
                "name": proj.get("name"),
                "collaboration_type": proj.get("collaboration_type"),
                "user_role": proj.get("user_role"),
            },
            "latest_snapshot_id": sid,
            "summary_text": summary_text,
            "resume_bullets": bullets,
            "thumbnail_blob": thumbnail_blob_json,
            "thumbnail_blob_sha256": thumbnail_blob_sha256,
            "signals": {
                "parser": {"generated_at": parser_out.get("generated_at"), "top_languages": parser_out.get("top_languages"), "activity_counts": parser_out.get("activity_counts")},
                "local_ml": {"generated_at": ml_out.get("generated_at"), "threshold": ml_out.get("threshold"), "top_skills": (ml_out.get("skills") or [])[:25]},
                "git_metrics": {"generated_at": git_out.get("generated_at"), "git_repos_found": git_out.get("git_repos_found"), "repo_summaries": (git_out.get("repo_summaries") or [])[:5]},
            },
            "metrics": {
                "total_commits": int(totals.get("total_commits") or 0),
                "user_commits": user_commits_out,
                "contributor_count": int(totals.get("contributor_count") or 0),
            },
        }


        payload = json.dumps(artifact, default=str)
        rid = conn.execute(
            text(
                """
                INSERT INTO resume_items (project_id, content_json)
                VALUES (:pid, CAST(:cj AS jsonb))
                RETURNING id
                """
            ),
            {"pid": project_id, "cj": payload},
        ).scalar_one()

        artifact["thumbnail_blob"] = thumbnail_blob_json
        artifact["thumbnail_blob_sha256"] = thumbnail_blob_sha256


    result = {"resume_id": str(rid), "content": artifact}
    logger.info("Generated resume item %s for project %s", str(rid), project_id)
    return result


def list_portfolio_showcases(
    *,
    engine: Engine,
    portfolio_id: str,
    limit: int,
) -> Dict[str, Any]:
    logger.debug("Listing portfolio showcases for portfolio %s (limit=%d)", portfolio_id, int(limit))
    with engine.connect() as conn:
        pf_ok = conn.execute(
            text("SELECT 1 FROM portfolios WHERE id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        if not pf_ok:
            raise KeyError("Portfolio not found")

        rows = conn.execute(
            text(
                """
                SELECT
                  ps.id,
                  ps.project_id,
                  pr.name AS project_name,
                  ps.thumbnail_blob_sha256,
                  ps.content_json,
                  ps.created_at,
                  ps.updated_at
                FROM portfolio_showcases ps
                JOIN projects pr ON pr.id = ps.project_id
                WHERE pr.portfolio_id = :pf
                ORDER BY ps.updated_at DESC NULLS LAST, ps.created_at DESC, ps.id DESC
                LIMIT :lim
                """
            ),
            {"pf": portfolio_id, "lim": int(limit)},
        ).mappings().all()

    items = []
    for r in rows:
        cj = r.get("content_json") or {}
        items.append(
            {
                "id": str(r["id"]),
                "project_id": str(r["project_id"]),
                "project_name": r.get("project_name"),
                "thumbnail_blob_sha256": r.get("thumbnail_blob_sha256"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
                "content": cj if isinstance(cj, dict) else {"raw": cj},
            }
        )

    return {"portfolio_id": portfolio_id, "limit": int(limit), "items": items}

def get_resume_item(
    *,
    engine: Engine,
    resume_id: str,
) -> Dict[str, Any]:
    logger.debug("Fetching resume item %s", resume_id)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, project_id, content_json, created_at, updated_at
                FROM resume_items
                WHERE id = :rid
                """
            ),
            {"rid": resume_id},
        ).mappings().first()

    if not row:
        raise KeyError("Resume item not found")
    
    project_id = row["project_id"]

    # Look up the showcase entry for this project
    with engine.connect() as conn:
        showcase = conn.execute(
            text("""
                SELECT thumbnail_blob_sha256
                FROM portfolio_showcases
                WHERE project_id = :pid
            """),
            {"pid": project_id},
        ).mappings().first()

    blob = None
    blob_sha = None

    if showcase and showcase.get("thumbnail_blob_sha256"):
        blob_sha = showcase["thumbnail_blob_sha256"]

        with engine.connect() as conn:
            blob = conn.execute(
                text("""
                    SELECT sha256, size_bytes, mime_type, stored_path
                    FROM file_blobs
                    WHERE sha256 = :sha
                """),
                {"sha": blob_sha},
            ).mappings().first()


    cj = row.get("content_json") or {}
    return {
        "resume_id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "content": cj if isinstance(cj, dict) else {"raw": cj},
        "thumbnail_blob_sha256": blob_sha,
        "thumbnail_blob": blob,
    }
