from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from src.api.ranking import compute_rank_score, normalize_ranking_config, sort_projects
from src.db.user_config import get_user_config

HEATMAP_BUCKETS = {"day", "week", "hour"}
LINE_KEYS = ("total_lines", "totalLines", "lines", "line_count", "lineCount", "loc", "sloc", "nloc")


def _dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _int(v: Any, d: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return d


def _float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _optional_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        try:
            return str(v.isoformat())
        except Exception:
            return None
    s = str(v).strip()
    return s or None


def _dt(v: Any) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _line_total(totals: Mapping[str, Any] | None) -> int:
    if not isinstance(totals, Mapping):
        return 0
    for key in LINE_KEYS:
        n = _int(totals.get(key), -1)
        if n >= 0:
            return n
    return 0


def _stage(conf: float, hits: int, observations: int) -> str:
    if conf >= 0.80 and hits >= 25:
        return "advanced"
    if conf >= 0.55 or hits >= 10 or observations >= 3:
        return "developing"
    return "emerging"


def _first_seen(skill: Mapping[str, Any]) -> Optional[str]:
    ts = _iso(skill.get("first_seen_ts"))
    if ts:
        return ts

    examples = skill.get("examples")
    if not isinstance(examples, list):
        evidence = skill.get("evidence_json")
        if isinstance(evidence, Mapping):
            examples = evidence.get("examples")

    if isinstance(examples, list):
        vals = [_dt(_dict(e).get("ts")) for e in examples if isinstance(e, Mapping)]
        vals = [x for x in vals if x is not None]
        if vals:
            return min(vals).isoformat()
    return None


def _analysis_skill_rows(conn, analysis_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    if not analysis_ids:
        return {}

    columns = set(
        conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'analysis_skills'
                """
            )
        ).scalars().all()
    )
    has_first_seen_ts = "first_seen_ts" in columns
    first_seen_col = "a_s.first_seen_ts AS first_seen_ts," if has_first_seen_ts else "NULL AS first_seen_ts,"

    rows = conn.execute(
        text(
            f"""
            SELECT
              a_s.analysis_id,
              s.skill_name AS skill,
              {first_seen_col}
              a_s.confidence,
              a_s.evidence_json
            FROM analysis_skills a_s
            JOIN skills s ON s.id = a_s.skill_id
            WHERE a_s.analysis_id IN :analysis_ids
            ORDER BY a_s.analysis_id, a_s.confidence DESC NULLS LAST, s.skill_name ASC
            """
        ).bindparams(bindparam("analysis_ids", expanding=True)),
        {"analysis_ids": analysis_ids},
    ).mappings().all()

    by_analysis: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        aid = str(row.get("analysis_id") or "").strip()
        if not aid:
            continue
        by_analysis.setdefault(aid, []).append(dict(row))
    return by_analysis


def _build_skills_timeline(conn, *, portfolio_id: str, limit: int) -> Dict[str, Any]:
    rows = conn.execute(
        text(
            """
            WITH latest_ml AS (
              SELECT DISTINCT ON (a.snapshot_id)
                a.id AS analysis_id,
                a.snapshot_id,
                a.output_json,
                COALESCE(a.completed_at, s.ingested_at) AS observed_at,
                a.created_at,
                p.id AS project_id,
                COALESCE(p.display_name, p.name) AS project_name
              FROM analyses a
              JOIN snapshots s ON s.id = a.snapshot_id
              JOIN projects p ON p.id = s.project_id
              WHERE p.portfolio_id = :pid
                AND a.analysis_type = 'local_ml'
                AND a.status = 'complete'
              ORDER BY a.snapshot_id, a.completed_at DESC NULLS LAST, a.created_at DESC
            )
            SELECT
              analysis_id,
              snapshot_id,
              output_json,
              observed_at,
              created_at,
              project_id,
              project_name
            FROM latest_ml
            ORDER BY observed_at ASC, created_at ASC
            """
        ),
        {"pid": portfolio_id},
    ).mappings().all()

    analysis_ids = [str(row.get("analysis_id")) for row in rows if row.get("analysis_id")]
    fallback_by_analysis = _analysis_skill_rows(conn, analysis_ids)

    state: Dict[str, Dict[str, Any]] = {}
    events: List[Dict[str, Any]] = []

    for row in rows:
        aid = str(row.get("analysis_id") or "").strip()
        observed_at = _iso(row.get("observed_at"))
        skills = _dict(row.get("output_json")).get("skills")
        if not isinstance(skills, list) or not skills:
            skills = fallback_by_analysis.get(aid, [])

        for skill_row in skills:
            if not isinstance(skill_row, Mapping):
                continue
            skill = str(skill_row.get("skill") or skill_row.get("skill_name") or "").strip()
            if not skill:
                continue

            evidence = _dict(skill_row.get("evidence_json"))
            conf = _float(
                skill_row.get("max_prob"),
                _float(skill_row.get("confidence"), _float(evidence.get("max_prob"), 0.0)),
            )
            hits = _int(skill_row.get("hits"), _int(evidence.get("hits"), 0))
            key = skill.casefold()
            seen = _first_seen(skill_row)
            prev = state.get(key) or {
                "first_seen_ts": seen,
                "last_confidence": None,
                "peak_confidence": 0.0,
                "cumulative_hits": 0,
                "observations": 0,
            }

            old_seen, new_seen = _dt(prev.get("first_seen_ts")), _dt(seen)
            if old_seen is None and new_seen is not None:
                prev["first_seen_ts"] = seen
            elif old_seen is not None and new_seen is not None and new_seen < old_seen:
                prev["first_seen_ts"] = seen

            delta = None if prev.get("last_confidence") is None else round(conf - _float(prev.get("last_confidence"), 0.0), 4)
            prev["last_confidence"] = conf
            prev["peak_confidence"] = max(_float(prev.get("peak_confidence"), 0.0), conf)
            prev["cumulative_hits"] = _int(prev.get("cumulative_hits"), 0) + max(hits, 0)
            prev["observations"] = _int(prev.get("observations"), 0) + 1
            state[key] = prev

            events.append(
                {
                    "skill": skill,
                    "project_id": str(row.get("project_id")),
                    "project_name": row.get("project_name"),
                    "snapshot_id": str(row.get("snapshot_id")),
                    "analysis_id": aid,
                    "observed_at": observed_at,
                    "first_seen_ts": prev.get("first_seen_ts"),
                    "signal": {
                        "confidence": round(conf, 4),
                        "confidence_delta": delta,
                        "hits": max(hits, 0),
                        "cumulative_hits": _int(prev.get("cumulative_hits"), 0),
                        "peak_confidence": round(_float(prev.get("peak_confidence"), 0.0), 4),
                        "observation_index": _int(prev.get("observations"), 0),
                        "stage": _stage(
                            _float(prev.get("peak_confidence"), 0.0),
                            _int(prev.get("cumulative_hits"), 0),
                            _int(prev.get("observations"), 0),
                        ),
                    },
                }
            )

    return {"limit": int(limit), "total_events": len(events), "events": events[: int(limit)]}


def _build_activity_heatmap(conn, *, portfolio_id: str, bucket: str) -> Dict[str, Any]:
    granularity = str(bucket or "day").strip().lower()
    if granularity not in HEATMAP_BUCKETS:
        granularity = "day"

    rows = conn.execute(
        text(
            f"""
            SELECT
              DATE_TRUNC('{granularity}', s.ingested_at) AS bucket_start,
              COUNT(DISTINCT s.id) AS snapshot_count,
              COALESCE(SUM(ce.commit_count), 0) AS commit_count,
              COALESCE(SUM(ce.lines_added), 0) AS lines_added,
              COALESCE(SUM(ce.lines_deleted), 0) AS lines_deleted,
              ARRAY_AGG(DISTINCT p.id) AS project_ids,
              ARRAY_AGG(DISTINCT COALESCE(p.display_name, p.name)) AS project_names
            FROM projects p
            JOIN snapshots s ON s.project_id = p.id
            LEFT JOIN contribution_events ce ON ce.snapshot_id = s.id
            WHERE p.portfolio_id = :pid
            GROUP BY DATE_TRUNC('{granularity}', s.ingested_at)
            ORDER BY DATE_TRUNC('{granularity}', s.ingested_at) ASC
            """
        ),
        {"pid": portfolio_id},
    ).mappings().all()

    out = []
    for row in rows:
        start = _iso(row.get("bucket_start"))
        day = _dt(start)
        snap = _int(row.get("snapshot_count"), 0)
        commits = _int(row.get("commit_count"), 0)
        out.append(
            {
                "bucket_start": start,
                "bucket_date": day.date().isoformat() if day else None,
                "bucket_granularity": granularity,
                "activity_count": snap + commits,
                "snapshot_count": snap,
                "commit_count": commits,
                "lines_added": _int(row.get("lines_added"), 0),
                "lines_deleted": _int(row.get("lines_deleted"), 0),
                "project_ids": sorted({str(v) for v in (row.get("project_ids") or []) if v is not None}),
                "project_names": sorted({str(v).strip() for v in (row.get("project_names") or []) if str(v).strip()}),
            }
        )

    return {"bucket": granularity, "total_buckets": len(out), "buckets": out}


def _ranked_projects(conn, *, portfolio_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            WITH totals AS (
              SELECT s.project_id, COALESCE(SUM(ce.commit_count), 0) AS total_commits,
                     COUNT(DISTINCT ce.contributor_id) AS contributor_count
              FROM snapshots s
              LEFT JOIN contribution_events ce ON ce.snapshot_id = s.id
              GROUP BY s.project_id
            ),
            user_totals AS (
              SELECT s.project_id, COALESCE(SUM(ce.commit_count), 0) AS user_commits
              FROM snapshots s
              JOIN contribution_events ce ON ce.snapshot_id = s.id
              JOIN project_contributors pc ON pc.project_id = s.project_id AND pc.contributor_id = ce.contributor_id AND pc.is_user = TRUE
              GROUP BY s.project_id
            )
            SELECT
              p.id,
              COALESCE(p.display_name, p.name) AS project_name,
              p.created_at,
              COALESCE(t.total_commits, 0) AS total_commits,
              COALESCE(ut.user_commits, 0) AS user_commits,
              COALESCE(t.contributor_count, 0) AS contributor_count
            FROM projects p
            LEFT JOIN totals t ON t.project_id = p.id
            LEFT JOIN user_totals ut ON ut.project_id = p.id
            WHERE p.portfolio_id = :pid
            ORDER BY p.created_at ASC
            """
        ),
        {"pid": portfolio_id},
    ).mappings().all()

    owner = conn.execute(text("SELECT user_id FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar()
    cfg = normalize_ranking_config((get_user_config(conn, str(owner)) if owner else {}).get("ranking") or {})

    projects = []
    for row in rows:
        total = _int(row.get("total_commits"), 0)
        user = _int(row.get("user_commits"), 0)
        user_out = user if user > 0 else None
        contributors = _int(row.get("contributor_count"), 0)
        projects.append(
            {
                "id": str(row.get("id")),
                "project_name": row.get("project_name"),
                "created_at": row.get("created_at"),
                "metrics": {
                    "total_commits": total,
                    "user_commits": user_out,
                    "contributor_count": contributors,
                    "rank_score": compute_rank_score(
                        user_commits=user_out,
                        total_commits=total,
                        contributor_count=contributors,
                        ranking_cfg=cfg,
                    ),
                },
            }
        )

    return sort_projects(projects, cfg)


def _build_project_evolution(conn, *, portfolio_id: str, top_limit: int) -> Dict[str, Any]:
    top = _ranked_projects(conn, portfolio_id=portfolio_id)[: int(top_limit)]
    out = []

    for project in top:
        rows = conn.execute(
            text(
                """
                SELECT
                  s.id AS snapshot_id,
                  s.snapshot_label,
                  s.ingested_at,
                  COALESCE(SUM(ce.commit_count), 0) AS commit_count,
                  (
                    SELECT output_json FROM analyses a
                    WHERE a.snapshot_id = s.id AND a.analysis_type = 'parser' AND a.status = 'complete'
                    ORDER BY a.completed_at DESC NULLS LAST, a.created_at DESC LIMIT 1
                  ) AS parser_out,
                  (
                    SELECT output_json FROM analyses a
                    WHERE a.snapshot_id = s.id AND a.analysis_type = 'local_ml' AND a.status = 'complete'
                    ORDER BY a.completed_at DESC NULLS LAST, a.created_at DESC LIMIT 1
                  ) AS ml_out
                FROM snapshots s
                LEFT JOIN contribution_events ce ON ce.snapshot_id = s.id
                WHERE s.project_id = :pid
                GROUP BY s.id, s.snapshot_label, s.ingested_at
                ORDER BY s.ingested_at ASC
                """
            ),
            {"pid": project["id"]},
        ).mappings().all()

        snaps = []
        for row in rows:
            parser = _dict(row.get("parser_out"))
            totals = _dict(parser.get("totals"))
            ml = _dict(row.get("ml_out"))
            ml_totals = _dict(ml.get("totals"))
            snaps.append(
                {
                    "snapshot_id": str(row.get("snapshot_id")),
                    "snapshot_label": row.get("snapshot_label"),
                    "timestamp": _iso(row.get("ingested_at")),
                    "commit_count": _int(row.get("commit_count"), 0),
                    "total_files": _int(totals.get("files"), 0),
                    "total_lines": _line_total(totals),
                    "skills_detected": _int(ml_totals.get("skills_detected"), len([s for s in (ml.get("skills") or []) if isinstance(s, Mapping)])),
                }
            )

        milestones = []
        if snaps:
            first, last = snaps[0], snaps[-1]
            milestones.append(
                {
                    "type": "project_started",
                    "timestamp": first.get("timestamp"),
                    "snapshot_id": first.get("snapshot_id"),
                    "snapshot_label": first.get("snapshot_label"),
                    "summary": f"Initial snapshot with {first['skills_detected']} skill(s) and {first['total_lines']} line(s).",
                    "metrics": {k: first[k] for k in ("commit_count", "total_files", "total_lines", "skills_detected")},
                }
            )
            if len(snaps) > 1:
                milestones.append(
                    {
                        "type": "latest_state",
                        "timestamp": last.get("timestamp"),
                        "snapshot_id": last.get("snapshot_id"),
                        "snapshot_label": last.get("snapshot_label"),
                        "summary": f"Latest snapshot shows {last['skills_detected']} skill(s) and {last['total_lines']} line(s).",
                        "metrics": {k: last[k] for k in ("commit_count", "total_files", "total_lines", "skills_detected")},
                    }
                )
            summary = (
                f"{len(snaps)} snapshot(s) from {first.get('timestamp') or 'N/A'} to {last.get('timestamp') or 'N/A'}; "
                f"skills {first['skills_detected']}->{last['skills_detected']}, lines {first['total_lines']}->{last['total_lines']}."
            )
        else:
            summary = "No snapshots available for project evolution."

        out.append(
            {
                "project_id": project["id"],
                "project_name": project.get("project_name"),
                "created_at": project.get("created_at"),
                "rank_score": _optional_float((project.get("metrics") or {}).get("rank_score")),
                "selection_features": (project.get("metrics") or {}).copy(),
                "evolution_summary": summary,
                "milestones": milestones,
            }
        )

    return {"limit": int(top_limit), "projects": out}


def build_portfolio_analytics(
    *,
    engine: Engine,
    portfolio_id: str,
    timeline_limit: int = 1000,
    heatmap_bucket: str = "day",
    top_limit: int = 3,
) -> Dict[str, Any]:
    with engine.connect() as conn:
        return {
            "portfolio_id": portfolio_id,
            "skills_timeline": _build_skills_timeline(conn, portfolio_id=portfolio_id, limit=int(timeline_limit)),
            "activity_heatmap": _build_activity_heatmap(conn, portfolio_id=portfolio_id, bucket=heatmap_bucket),
            "top_project_evolution": _build_project_evolution(conn, portfolio_id=portfolio_id, top_limit=int(top_limit)),
        }
