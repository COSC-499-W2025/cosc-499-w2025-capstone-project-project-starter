from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine


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

    if total_commits is not None and contributor_count is not None:
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

    if total_commits is not None and contributor_count is not None:
        if user_commits is not None and user_commits > 0:
            b2 = f"Delivered {user_commits} of {total_commits} commits in a {collab_type or 'collaborative'} setting with {contributor_count} contributor(s)."
        else:
            b2 = f"Worked across {total_commits} commits with {contributor_count} contributor(s); collaboration type: {collab_type or 'unknown'}."
    else:
        b2 = "Coordinated work across multiple iterations and snapshots, maintaining a repeatable analysis pipeline."

    focus_skill = (top_skills or [None])[0]
    if focus_skill:
        b3 = f"Demonstrated proficiency in {focus_skill} through measurable repository activity and structured project outputs."
    else:
        b3 = "None"

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
        return None


def _ranked_projects_for_portfolio(conn, portfolio_id: str) -> List[Dict[str, Any]]:
    """
    Ranking rule:
      - If user_commits>0 exists (requires project_contributors.is_user), compute rank_score:
          user_commits + 0.10*(total_commits - user_commits)
      - Else: rank_score = NULL; fallback sort by total_commits desc then created_at asc
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

    out: List[Dict[str, Any]] = []
    for r in rows:
        total = int(r["total_commits"] or 0)
        userc_raw = int(r["user_commits"] or 0)
        userc = userc_raw if userc_raw > 0 else None

        rank_score = None
        if userc is not None:
            rank_score = float(userc) + 0.10 * float(max(0, total - userc))

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

    def sort_key(p: Dict[str, Any]):
        rs = (p.get("metrics") or {}).get("rank_score")
        tc = int((p.get("metrics") or {}).get("total_commits") or 0)
        ca = p.get("created_at") or ""
        # rank_score desc NULLS LAST, then total_commits desc, then created_at asc
        return (
            1 if rs is None else 0,
            0.0 if rs is None else -float(rs),
            -int(tc),
            str(ca),
        )

    out.sort(key=sort_key)
    return out


def generate_portfolio_top_summaries(
    *,
    engine: Engine,
    portfolio_id: str,
    limit: int,
    persist: bool,
) -> Dict[str, Any]:
    generated_at = _utcnow_iso()

    with engine.begin() as conn:
        pf_ok = conn.execute(text("SELECT 1 FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
        if not pf_ok:
            raise KeyError("Portfolio not found")

        ranked = _ranked_projects_for_portfolio(conn, portfolio_id)[: int(limit)]

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

            top_skills = []
            try:
                top_skills = [str(x.get("skill")) for x in (ml_out.get("skills") or [])[:10] if isinstance(x, dict) and x.get("skill")]
            except Exception:
                top_skills = []

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
                showcase_id = conn.execute(
                    text(
                        """
                        INSERT INTO portfolio_showcases (project_id, thumbnail_blob_sha256, content_json)
                        VALUES (:pid, NULL, CAST(:cj AS jsonb))
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

    return {
        "portfolio_id": portfolio_id,
        "generated_at": generated_at,
        "limit": int(limit),
        "persisted": bool(persist),
        "showcase_ids": showcase_ids,
        "top_projects": top_projects,
    }


def generate_resume_item(
    *,
    engine: Engine,
    project_id: str,
    prefer_external_bullets: bool,
) -> Dict[str, Any]:
    generated_at = _utcnow_iso()

    with engine.begin() as conn:
        proj = conn.execute(
            text("SELECT id, name, portfolio_id, collaboration_type, user_role FROM projects WHERE id = :pid"),
            {"pid": project_id},
        ).mappings().first()
        if not proj:
            raise KeyError("Project not found")

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

        top_skills = []
        try:
            top_skills = [str(x.get("skill")) for x in (ml_out.get("skills") or [])[:15] if isinstance(x, dict) and x.get("skill")]
        except Exception:
            top_skills = []

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

    return {"resume_id": str(rid), "content": artifact}


def list_portfolio_showcases(
    *,
    engine: Engine,
    portfolio_id: str,
    limit: int,
) -> Dict[str, Any]:
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

    # Tests expect "items", not "showcases".
    return {"portfolio_id": portfolio_id, "limit": int(limit), "items": items}

def get_resume_item(
    *,
    engine: Engine,
    resume_id: str,
) -> Dict[str, Any]:
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

    cj = row.get("content_json") or {}
    return {
        "resume_id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "content": cj if isinstance(cj, dict) else {"raw": cj},
    }
