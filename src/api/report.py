from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.db.base import fetch_snapshot_files


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Handles "2026-01-14T15:31:14+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _safe_read_text(path: str, max_bytes: int = 200_000) -> str:
    # Best-effort, never throws.
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _detect_frameworks_from_manifests(engine: Engine, snapshot_id: str) -> Dict[str, Any]:
    """
    Lightweight, local-only heuristic framework detection.
    Returns: {"frameworks": [...], "evidence": [{"file":..., "matched": [...]}]}
    """
    files = fetch_snapshot_files(engine, snapshot_id)

    # Map candidate manifest basenames -> stored_path
    candidates: Dict[str, str] = {}
    for f in files:
        base = os.path.basename(f.relative_path).lower()
        if base in {
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "cargo.toml",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "composer.json",
            "gemfile",
            "go.mod",
        }:
            candidates[base] = f.stored_path

    frameworks: List[str] = []
    evidence: List[Dict[str, Any]] = []

    def add(file_key: str, matched: List[str]):
        nonlocal frameworks, evidence
        if not matched:
            return
        for m in matched:
            if m not in frameworks:
                frameworks.append(m)
        evidence.append({"file": file_key, "matched": matched})

    # package.json
    if "package.json" in candidates:
        matched: List[str] = []
        try:
            obj = json.loads(_safe_read_text(candidates["package.json"], max_bytes=400_000) or "{}")
            deps = {}
            for k in ("dependencies", "devDependencies", "peerDependencies"):
                v = obj.get(k)
                if isinstance(v, dict):
                    deps.update(v)
            keys = {str(k).lower() for k in deps.keys()}

            # Common JS frameworks/libs
            if "react" in keys:
                matched.append("React")
            if "next" in keys or "nextjs" in keys:
                matched.append("Next.js")
            if "vue" in keys or "vuejs" in keys:
                matched.append("Vue")
            if "angular" in keys or "@angular/core" in keys:
                matched.append("Angular")
            if "express" in keys:
                matched.append("Express")
            if "@nestjs/core" in keys or "nestjs" in keys:
                matched.append("NestJS")
            if "svelte" in keys:
                matched.append("Svelte")
            if "nuxt" in keys:
                matched.append("Nuxt")
        except Exception:
            matched = []
        add("package.json", matched)

    # requirements.txt
    if "requirements.txt" in candidates:
        txt = _safe_read_text(candidates["requirements.txt"])
        keys = set()
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r"[<=>\[\];\s]", line, maxsplit=1)[0].strip().lower()
            if pkg:
                keys.add(pkg)

        matched: List[str] = []
        if "django" in keys:
            matched.append("Django")
        if "flask" in keys:
            matched.append("Flask")
        if "fastapi" in keys:
            matched.append("FastAPI")
        if "streamlit" in keys:
            matched.append("Streamlit")
        if "pytest" in keys:
            matched.append("pytest")
        add("requirements.txt", matched)

    # pyproject.toml (best-effort substring scan)
    if "pyproject.toml" in candidates:
        txt = _safe_read_text(candidates["pyproject.toml"], max_bytes=400_000).lower()
        matched: List[str] = []
        if "django" in txt:
            matched.append("Django")
        if "flask" in txt:
            matched.append("Flask")
        if "fastapi" in txt:
            matched.append("FastAPI")
        if "poetry" in txt:
            matched.append("Poetry")
        if "pytest" in txt:
            matched.append("pytest")
        add("pyproject.toml", matched)

    # Cargo.toml (best-effort substring scan)
    if "cargo.toml" in candidates:
        txt = _safe_read_text(candidates["cargo.toml"], max_bytes=400_000).lower()
        matched: List[str] = []
        if "axum" in txt:
            matched.append("Axum")
        if "actix-web" in txt:
            matched.append("Actix Web")
        if "rocket" in txt:
            matched.append("Rocket")
        if "warp" in txt:
            matched.append("Warp")
        if "tokio" in txt:
            matched.append("Tokio")
        add("Cargo.toml", matched)

    # Java build files (very coarse)
    if "pom.xml" in candidates:
        txt = _safe_read_text(candidates["pom.xml"], max_bytes=400_000).lower()
        matched: List[str] = []
        if "spring" in txt:
            matched.append("Spring")
        if "quarkus" in txt:
            matched.append("Quarkus")
        add("pom.xml", matched)

    if "build.gradle" in candidates or "build.gradle.kts" in candidates:
        key = "build.gradle.kts" if "build.gradle.kts" in candidates else "build.gradle"
        txt = _safe_read_text(candidates[key], max_bytes=400_000).lower()
        matched: List[str] = []
        if "spring" in txt:
            matched.append("Spring")
        if "android" in txt:
            matched.append("Android")
        add(key, matched)

    # Ruby/PHP/Go (minimal)
    if "gemfile" in candidates:
        txt = _safe_read_text(candidates["gemfile"], max_bytes=200_000).lower()
        matched: List[str] = []
        if "rails" in txt:
            matched.append("Rails")
        add("Gemfile", matched)

    if "composer.json" in candidates:
        txt = _safe_read_text(candidates["composer.json"], max_bytes=400_000).lower()
        matched: List[str] = []
        if "laravel" in txt:
            matched.append("Laravel")
        if "symfony" in txt:
            matched.append("Symfony")
        add("composer.json", matched)

    if "go.mod" in candidates:
        txt = _safe_read_text(candidates["go.mod"], max_bytes=200_000).lower()
        matched: List[str] = []
        # common Go web libs
        if "gin-gonic" in txt or "gin" in txt:
            matched.append("Gin")
        if "fiber" in txt:
            matched.append("Fiber")
        add("go.mod", matched)

    return {"frameworks": frameworks, "evidence": evidence}


def build_project_report(
    *,
    engine: Engine,
    project_id: str,
    include_raw_analyses: bool = False,
    include_framework_detection: bool = True,
) -> Dict[str, Any]:
    """
    Canonical project report:
      - project metadata
      - snapshots chronological
      - per-snapshot selected analyses (parser/local_ml/git_metrics)
      - derived: skills chronology, contribution summary, duration, frameworks (best-effort)
    """
    with engine.connect() as conn:
        project = conn.execute(
            text(
                """
                SELECT id, portfolio_id, name, project_type, collaboration_type, user_role, evidence_json, created_at
                FROM projects
                WHERE id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first()

        if not project:
            raise KeyError("Project not found")

        snapshots = conn.execute(
            text(
                """
                SELECT id, project_id, source_zip_name, source_zip_sha256, ingested_at, snapshot_label
                FROM snapshots
                WHERE project_id = :pid
                ORDER BY ingested_at ASC
                """
            ),
            {"pid": project_id},
        ).mappings().all()

    snapshot_reports: List[Dict[str, Any]] = []
    skill_first_seen: Dict[str, datetime] = {}
    skill_best: Dict[str, Dict[str, Any]] = {}  # keep best evidence (max_prob) for the skill

    # Contribution summary across snapshots (if git_metrics has written rows)
    with engine.connect() as conn:
        contrib_totals = conn.execute(
            text(
                """
                SELECT
                  COUNT(DISTINCT ce.contributor_id) AS contributor_count,
                  COALESCE(SUM(ce.commit_count), 0) AS total_commits
                FROM contribution_events ce
                JOIN snapshots s ON s.id = ce.snapshot_id
                WHERE s.project_id = :pid
                """
            ),
            {"pid": project_id},
        ).mappings().first() or {"contributor_count": 0, "total_commits": 0}

        user_commits = conn.execute(
            text(
                """
                SELECT COALESCE(SUM(ce.commit_count), 0) AS user_commits
                FROM contribution_events ce
                JOIN snapshots s ON s.id = ce.snapshot_id
                JOIN project_contributors pc
                  ON pc.project_id = s.project_id
                 AND pc.contributor_id = ce.contributor_id
                WHERE s.project_id = :pid AND pc.is_user = TRUE
                """
            ),
            {"pid": project_id},
        ).scalar()

        # Top contributors by commits (best-effort)
        top_contrib = conn.execute(
            text(
                """
                SELECT c.canonical_name, c.email, SUM(ce.commit_count) AS commits
                FROM contribution_events ce
                JOIN snapshots s ON s.id = ce.snapshot_id
                JOIN contributors c ON c.id = ce.contributor_id
                WHERE s.project_id = :pid
                GROUP BY c.canonical_name, c.email
                ORDER BY commits DESC, c.canonical_name ASC
                LIMIT 10
                """
            ),
            {"pid": project_id},
        ).mappings().all()

    # Snapshot loop (simple and robust; snapshots should be small count)
    for s in snapshots:
        sid = str(s["id"])

        with engine.connect() as conn:
            analyses = conn.execute(
                text(
                    """
                    SELECT id, analysis_type, status, created_at, completed_at, output_json
                    FROM analyses
                    WHERE snapshot_id = :sid
                    ORDER BY created_at ASC
                    """
                ),
                {"sid": sid},
            ).mappings().all()

        # pick “best” completed analysis per type (latest completed_at; fallback created_at)
        per_type: Dict[str, Dict[str, Any]] = {}
        for a in analyses:
            at = a["analysis_type"]
            status = a["status"]
            if status != "complete":
                continue
            cur = per_type.get(at)
            if not cur:
                per_type[at] = dict(a)
                continue
            # compare completed_at then created_at
            cur_ca = cur.get("completed_at") or cur.get("created_at")
            a_ca = a.get("completed_at") or a.get("created_at")
            if (a_ca is not None) and (cur_ca is None or a_ca > cur_ca):
                per_type[at] = dict(a)

        parser_out = (per_type.get("parser") or {}).get("output_json") or {}
        ml_out = (per_type.get("local_ml") or {}).get("output_json") or {}
        git_out = (per_type.get("git_metrics") or {}).get("output_json") or {}

        # Accumulate skill chronology from local_ml output_json.skills[*].first_seen_ts
        skills = ml_out.get("skills", [])
        if isinstance(skills, list):
            for row in skills:
                if not isinstance(row, dict):
                    continue
                name = row.get("skill")
                if not name:
                    continue

                fst = _parse_iso(row.get("first_seen_ts"))
                if fst is None:
                    # fallback to min example ts if present
                    ex = row.get("examples")
                    if isinstance(ex, list) and ex:
                        ex_ts = [_parse_iso(e.get("ts")) for e in ex if isinstance(e, dict)]
                        ex_ts = [t for t in ex_ts if t is not None]
                        fst = min(ex_ts) if ex_ts else None

                if fst is not None:
                    prev = skill_first_seen.get(name)
                    if prev is None or fst < prev:
                        skill_first_seen[name] = fst

                # Keep best evidence row by max_prob
                try:
                    mp = float(row.get("max_prob") or 0.0)
                except Exception:
                    mp = 0.0
                cur_best = skill_best.get(name)
                if not cur_best:
                    skill_best[name] = row
                else:
                    try:
                        cur_mp = float(cur_best.get("max_prob") or 0.0)
                    except Exception:
                        cur_mp = 0.0
                    if mp > cur_mp:
                        skill_best[name] = row

        snapshot_entry: Dict[str, Any] = {
            "snapshot": {
                "id": sid,
                "ingested_at": _iso(s.get("ingested_at")),
                "snapshot_label": s.get("snapshot_label"),
                "source_zip_name": s.get("source_zip_name"),
                "source_zip_sha256": s.get("source_zip_sha256"),
            },
            "analyses": {
                "available": sorted({a["analysis_type"] for a in analyses}),
                "complete": sorted(per_type.keys()),
                "parser": {
                    "generated_at": parser_out.get("generated_at"),
                    "totals": parser_out.get("totals"),
                    "top_languages": parser_out.get("top_languages"),
                    "activity_counts": parser_out.get("activity_counts"),
                    "language_counts": parser_out.get("language_counts"),
                } if parser_out else None,
                "local_ml": {
                    "generated_at": ml_out.get("generated_at"),
                    "threshold": ml_out.get("threshold"),
                    "totals": ml_out.get("totals"),
                    "skills_detected": (ml_out.get("totals") or {}).get("skills_detected"),
                    # keep report compact; caller can request raw
                    "top_skills": (ml_out.get("skills") or [])[:20] if isinstance(ml_out.get("skills"), list) else [],
                } if ml_out else None,
                "git_metrics": {
                    "generated_at": git_out.get("generated_at"),
                    "git_repos_found": git_out.get("git_repos_found"),
                    "repo_summaries": git_out.get("repo_summaries"),
                    "commit_contributions": git_out.get("commit_contributions"),
                } if git_out else None,
            },
        }

        if include_raw_analyses:
            snapshot_entry["analyses_raw"] = {
                "parser": parser_out,
                "local_ml": ml_out,
                "git_metrics": git_out,
            }

        snapshot_reports.append(snapshot_entry)

    # Project duration based on snapshot ingestion times
    ingested_times = [_parse_iso(r["snapshot"]["ingested_at"]) for r in snapshot_reports]
    ingested_times = [t for t in ingested_times if t is not None]
    start = min(ingested_times) if ingested_times else None
    end = max(ingested_times) if ingested_times else None
    duration_seconds = int((end - start).total_seconds()) if start and end else None

    # Skills chronology list
    skills_chrono = [
        {
            "skill": name,
            "first_seen_ts": skill_first_seen[name].isoformat(),
            "max_prob": float((skill_best.get(name) or {}).get("max_prob") or 0.0),
            "avg_prob": float((skill_best.get(name) or {}).get("avg_prob") or 0.0),
            "hits": int((skill_best.get(name) or {}).get("hits") or 0),
            "examples": (skill_best.get(name) or {}).get("examples") or [],
        }
        for name in sorted(skill_first_seen.keys(), key=lambda k: skill_first_seen[k])
    ]

    # Skill “top” list (rank by max_prob then hits)
    skills_top = list(skills_chrono)
    skills_top.sort(key=lambda r: (r["max_prob"], r["hits"]), reverse=True)
    skills_top = skills_top[:50]

    # Collaboration inference (best-effort): DB value plus derived from contributor count
    contributor_count = int(contrib_totals.get("contributor_count") or 0)
    derived_collab = "collaborative" if contributor_count > 1 else "individual"

    # Rank features (best-effort). If user commits are known (project_contributors.is_user set), compute score.
    total_commits = int(contrib_totals.get("total_commits") or 0)
    user_commits_val = int(user_commits or 0)
    has_user_flag = user_commits is not None and user_commits_val > 0

    rank_score = None
    if has_user_flag:
        # Simple transparent heuristic: prioritize user commits, with small credit for overall repo activity.
        rank_score = float(user_commits_val) + 0.10 * float(max(0, total_commits - user_commits_val))

    frameworks_info = None
    if include_framework_detection and snapshot_reports:
        latest_snapshot_id = snapshot_reports[-1]["snapshot"]["id"]
        frameworks_info = _detect_frameworks_from_manifests(engine, latest_snapshot_id)

    # Assemble final report
    report = {
        "project": {
            "id": str(project["id"]),
            "portfolio_id": str(project["portfolio_id"]),
            "name": project["name"],
            "project_type": project["project_type"],
            "collaboration_type": project["collaboration_type"],
            "user_role": project.get("user_role"),
            "evidence_json": project.get("evidence_json") or {},
            "created_at": _iso(project.get("created_at")),
        },
        "snapshots": snapshot_reports,
        "derived": {
            "project_duration": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "duration_seconds": duration_seconds,
            },
            "collaboration": {
                "db_collaboration_type": project["collaboration_type"],
                "derived_collaboration_type": derived_collab,
                "contributor_count": contributor_count,
            },
            "contributions": {
                "total_commits": total_commits,
                "user_commits": user_commits_val if has_user_flag else None,
                "top_contributors": [dict(r) for r in top_contrib],
            },
            "skills": {
                "chronological": skills_chrono,
                "top": skills_top,
            },
            "frameworks": frameworks_info or {"frameworks": [], "evidence": []},
            "ranking": {
                "rank_score": rank_score,
                "features": {
                    "total_commits": total_commits,
                    "user_commits": user_commits_val if has_user_flag else None,
                    "contributor_count": contributor_count,
                    "snapshot_count": len(snapshot_reports),
                },
                "note": "rank_score is only computed when at least one contributor is flagged is_user=TRUE in project_contributors.",
            },
        },
    }

    return report
