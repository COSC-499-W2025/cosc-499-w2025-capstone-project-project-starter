from __future__ import annotations

import re
import secrets
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


DASHBOARD_MODE_PRIVATE = "private"
DASHBOARD_MODE_PUBLIC = "public"
ALLOWED_DASHBOARD_MODES = {DASHBOARD_MODE_PRIVATE, DASHBOARD_MODE_PUBLIC}
DEFAULT_PUBLIC_VISIBILITY = {
    "projects": True,
    "skills_timeline": True,
    "top_projects": True,
    "activity_heatmap": True,
    "showcases": True,
}

PUBLIC_FILTER_ALLOWED_KEYS = {"q", "date_from", "date_to", "project_ids", "skills", "sort"}
PUBLIC_FILTER_ALLOWED_SORTS = {
    "rank_desc",
    "rank_asc",
    "name_asc",
    "name_desc",
    "date_desc",
    "date_asc",
}
DEFAULT_PUBLIC_SORT = "rank_desc"


def public_filter_spec() -> Dict[str, Any]:
    return {
        "version": "v1",
        "allowed_filters": sorted(PUBLIC_FILTER_ALLOWED_KEYS),
        "allowed_sorts": sorted(PUBLIC_FILTER_ALLOWED_SORTS),
        "default_sort": DEFAULT_PUBLIC_SORT,
    }


def _to_dashboard_out(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "portfolio_id": str(row.get("portfolio_id")),
        "mode": str(row.get("mode") or DASHBOARD_MODE_PRIVATE),
        "public_slug": str(row.get("public_slug") or ""),
        "visibility_config": normalize_public_visibility_config(row.get("visibility_config_json")),
        "active_publication_id": str(row["active_publication_id"]) if row.get("active_publication_id") else None,
        "published_at": row.get("published_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _slug_candidate() -> str:
    raw = secrets.token_urlsafe(10).lower()
    clean = re.sub(r"[^a-z0-9_-]+", "", raw).strip("_-")
    if len(clean) < 12:
        clean = (clean + secrets.token_hex(8)).lower()
    return clean[:32]


def _portfolio_exists(conn, portfolio_id: str) -> bool:
    return bool(conn.execute(text("SELECT 1 FROM portfolios WHERE id = :pid"), {"pid": portfolio_id}).scalar())


def ensure_portfolio_dashboard(conn, portfolio_id: str) -> Dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT portfolio_id, mode, public_slug, visibility_config_json,
                   active_publication_id, published_at, created_at, updated_at
            FROM portfolio_dashboards
            WHERE portfolio_id = :pid
            """
        ),
        {"pid": portfolio_id},
    ).mappings().first()
    if row:
        return _to_dashboard_out(row)

    if not _portfolio_exists(conn, portfolio_id):
        raise KeyError("Portfolio not found")

    for _ in range(10):
        public_slug = _slug_candidate()
        conn.execute(
            text(
                """
                INSERT INTO portfolio_dashboards (
                  portfolio_id,
                  mode,
                  public_slug,
                  visibility_config_json
                )
                VALUES (:pid, :mode, :public_slug, CAST(:visibility AS jsonb))
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "pid": portfolio_id,
                "mode": DASHBOARD_MODE_PRIVATE,
                "public_slug": public_slug,
                "visibility": _json_dump(DEFAULT_PUBLIC_VISIBILITY),
            },
        )
        row = conn.execute(
            text(
                """
                SELECT portfolio_id, mode, public_slug, visibility_config_json,
                       active_publication_id, published_at, created_at, updated_at
                FROM portfolio_dashboards
                WHERE portfolio_id = :pid
                """
            ),
            {"pid": portfolio_id},
        ).mappings().first()
        if row:
            return _to_dashboard_out(row)

    raise RuntimeError("Unable to create dashboard row with a unique public slug")


def get_portfolio_dashboard(conn, portfolio_id: str) -> Dict[str, Any]:
    return ensure_portfolio_dashboard(conn, portfolio_id)


def set_portfolio_dashboard_mode(
    conn,
    *,
    portfolio_id: str,
    mode: str,
    active_publication_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in ALLOWED_DASHBOARD_MODES:
        raise ValueError("Invalid dashboard mode")

    ensure_portfolio_dashboard(conn, portfolio_id)

    conn.execute(
        text(
            """
            UPDATE portfolio_dashboards
            SET
              mode = :mode,
              active_publication_id = COALESCE(:apid, active_publication_id),
              published_at = CASE WHEN :mode = 'public' THEN NOW() ELSE published_at END,
              updated_at = NOW()
            WHERE portfolio_id = :pid
            """
        ),
        {"pid": portfolio_id, "mode": normalized_mode, "apid": active_publication_id},
    )
    return ensure_portfolio_dashboard(conn, portfolio_id)


def regenerate_portfolio_slug(conn, portfolio_id: str) -> Dict[str, Any]:
    ensure_portfolio_dashboard(conn, portfolio_id)

    for _ in range(10):
        slug = _slug_candidate()
        try:
            conn.execute(
                text(
                    """
                    UPDATE portfolio_dashboards
                    SET
                                            public_slug = :slug,
                      updated_at = NOW()
                    WHERE portfolio_id = :pid
                    """
                ),
                {
                    "pid": portfolio_id,
                    "slug": slug,
                },
            )
            return ensure_portfolio_dashboard(conn, portfolio_id)
        except IntegrityError:
            continue

    raise RuntimeError("Unable to generate a unique public slug")


def regenerate_portfolio_public_slug(conn, portfolio_id: str) -> Dict[str, Any]:
    return regenerate_portfolio_slug(conn, portfolio_id)


def set_portfolio_dashboard_visibility(
    conn,
    *,
    portfolio_id: str,
    visibility_config: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    ensure_portfolio_dashboard(conn, portfolio_id)
    normalized_visibility = normalize_public_visibility_config(visibility_config)
    conn.execute(
        text(
            """
            UPDATE portfolio_dashboards
            SET visibility_config_json = CAST(:visibility AS jsonb), updated_at = NOW()
            WHERE portfolio_id = :pid
            """
        ),
        {"pid": portfolio_id, "visibility": _json_dump(normalized_visibility)},
    )
    return ensure_portfolio_dashboard(conn, portfolio_id)


def _next_publication_version(conn, portfolio_id: str) -> int:
    value = conn.execute(
        text("SELECT COALESCE(MAX(version), 0) + 1 FROM dashboard_publications WHERE portfolio_id = :pid"),
        {"pid": portfolio_id},
    ).scalar()
    return int(value or 1)


def create_dashboard_publication(
    conn,
    *,
    portfolio_id: str,
    created_by_user_id: str,
    frozen_config_json: Dict[str, Any],
    frozen_dashboard_json: Dict[str, Any],
    filter_spec_json: Dict[str, Any],
) -> Dict[str, Any]:
    ensure_portfolio_dashboard(conn, portfolio_id)
    version = _next_publication_version(conn, portfolio_id)

    row = conn.execute(
        text(
            """
            INSERT INTO dashboard_publications (
              portfolio_id,
              version,
              frozen_config_json,
              frozen_dashboard_json,
              filter_spec_json,
              created_by_user_id
            )
            VALUES (
              :pid,
              :version,
              CAST(:cfg AS jsonb),
              CAST(:dash AS jsonb),
              CAST(:spec AS jsonb),
              :uid
            )
            RETURNING id, portfolio_id, version, created_by_user_id, created_at
            """
        ),
        {
            "pid": portfolio_id,
            "version": version,
            "cfg": _json_dump(frozen_config_json),
            "dash": _json_dump(frozen_dashboard_json),
            "spec": _json_dump(filter_spec_json),
            "uid": created_by_user_id,
        },
    ).mappings().first()

    if not row:
        raise RuntimeError("Failed to create dashboard publication")

    return {
        "publication_id": str(row["id"]),
        "portfolio_id": str(row["portfolio_id"]),
        "version": int(row["version"]),
        "created_by_user_id": str(row["created_by_user_id"]) if row.get("created_by_user_id") else None,
        "created_at": row.get("created_at"),
    }


def get_public_dashboard_by_slug(conn, public_slug: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        text(
            """
            SELECT
              pd.portfolio_id,
              pd.mode,
              pd.public_slug,
                            pd.visibility_config_json,
              pd.active_publication_id,
              pd.published_at,
              p.user_id AS owner_user_id,
              aa.display_name AS owner_display_name,
              pub.version,
              pub.frozen_config_json,
              pub.frozen_dashboard_json,
              pub.filter_spec_json,
              pub.created_at AS publication_created_at
            FROM portfolio_dashboards pd
            JOIN portfolios p ON p.id = pd.portfolio_id
            LEFT JOIN auth_accounts aa ON aa.user_id = p.user_id
            LEFT JOIN dashboard_publications pub ON pub.id = pd.active_publication_id
            WHERE pd.public_slug = :slug
            """
        ),
        {"slug": public_slug},
    ).mappings().first()
    if not row:
        return None
    return {
        "portfolio_id": str(row["portfolio_id"]),
        "mode": str(row.get("mode") or DASHBOARD_MODE_PRIVATE),
        "public_slug": str(row.get("public_slug") or ""),
        "visibility_config": normalize_public_visibility_config(row.get("visibility_config_json")),
        "active_publication_id": str(row["active_publication_id"]) if row.get("active_publication_id") else None,
        "published_at": row.get("published_at"),
        "owner_user_id": str(row["owner_user_id"]) if row.get("owner_user_id") else None,
        "owner_display_name": str(row.get("owner_display_name") or "").strip() or None,
        "owner_username": _public_username(
            display_name=row.get("owner_display_name"),
        ),
        "version": int(row["version"]) if row.get("version") is not None else None,
        "frozen_config_json": _as_dict(row.get("frozen_config_json")),
        "frozen_dashboard_json": _as_dict(row.get("frozen_dashboard_json")),
        "filter_spec_json": _as_dict(row.get("filter_spec_json")),
        "publication_created_at": row.get("publication_created_at"),
    }


def normalize_public_visibility_config(config: Any) -> Dict[str, bool]:
    source = config if isinstance(config, Mapping) else {}
    return {
        key: bool(source[key]) if key in source else bool(default_enabled)
        for key, default_enabled in DEFAULT_PUBLIC_VISIBILITY.items()
    }


def apply_public_visibility(
    dashboard_json: Mapping[str, Any] | None,
    visibility_config: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    out = deepcopy(dict(dashboard_json or {}))
    visibility = normalize_public_visibility_config(visibility_config)

    section_to_key = {
        "projects": "projects",
        "skills_timeline": "skills_timeline",
        "top_projects": "top_projects",
        "activity_heatmap": "activity_heatmap",
        "showcases": "showcases",
    }
    for section, key in section_to_key.items():
        if not visibility.get(section, False):
            out.pop(key, None)

    return out


def parse_public_filters(query_params: Any) -> Dict[str, Any]:
    keys = set(query_params.keys())
    unknown = sorted(keys - PUBLIC_FILTER_ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"Unsupported filter(s): {', '.join(unknown)}")

    q = str(query_params.get("q") or "").strip()
    date_from = _parse_date(query_params.get("date_from"))
    date_to = _parse_date(query_params.get("date_to"))
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from must be less than or equal to date_to")

    project_ids = _parse_multi_value(query_params, "project_ids")
    skills = _parse_multi_value(query_params, "skills", casefold=True)
    sort = str(query_params.get("sort") or DEFAULT_PUBLIC_SORT).strip().lower()
    if sort not in PUBLIC_FILTER_ALLOWED_SORTS:
        raise ValueError(f"Unsupported sort value: {sort}")

    return {
        "q": q or None,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "project_ids": project_ids,
        "skills": skills,
        "sort": sort,
    }


def apply_public_filters(
    frozen_dashboard_json: Mapping[str, Any] | None,
    filters: Mapping[str, Any],
) -> Dict[str, Any]:
    source = deepcopy(dict(frozen_dashboard_json or {}))

    projects = _ensure_rows(source.get("projects"))
    top_projects = _ensure_rows(source.get("top_projects"))
    skills_timeline = _ensure_rows(source.get("skills_timeline"))
    activity_heatmap = _ensure_rows(source.get("activity_heatmap"))
    top_project_evolution = _ensure_rows(source.get("top_project_evolution"))
    showcases = _ensure_rows(source.get("showcases"))

    pid_filter = {str(v).strip() for v in (filters.get("project_ids") or []) if str(v).strip()}
    skill_filter = {str(v).strip().casefold() for v in (filters.get("skills") or []) if str(v).strip()}
    text_query = str(filters.get("q") or "").strip().casefold()
    from_date = _parse_date(filters.get("date_from"))
    to_date = _parse_date(filters.get("date_to"))

    if pid_filter:
        projects = [p for p in projects if str(p.get("id") or "").strip() in pid_filter]
        top_projects = [p for p in top_projects if str(p.get("project_id") or "").strip() in pid_filter]
        skills_timeline = [e for e in skills_timeline if str(e.get("project_id") or "").strip() in pid_filter]
        top_project_evolution = [
            row for row in top_project_evolution if str(row.get("project_id") or "").strip() in pid_filter
        ]
        showcases = [s for s in showcases if str(s.get("project_id") or "").strip() in pid_filter]
        activity_heatmap = [
            bucket
            for bucket in activity_heatmap
            if pid_filter.intersection({str(v).strip() for v in (bucket.get("project_ids") or []) if str(v).strip()})
        ]

    if skill_filter:
        skills_timeline = [
            event
            for event in skills_timeline
            if str(event.get("skill") or "").strip().casefold() in skill_filter
        ]
        inferred_ids = {str(event.get("project_id") or "").strip() for event in skills_timeline if event.get("project_id")}
        projects = [p for p in projects if str(p.get("id") or "").strip() in inferred_ids]
        top_projects = [p for p in top_projects if str(p.get("project_id") or "").strip() in inferred_ids]
        top_project_evolution = [
            row for row in top_project_evolution if str(row.get("project_id") or "").strip() in inferred_ids
        ]
        showcases = [s for s in showcases if str(s.get("project_id") or "").strip() in inferred_ids]
        activity_heatmap = [
            bucket
            for bucket in activity_heatmap
            if inferred_ids.intersection({str(v).strip() for v in (bucket.get("project_ids") or []) if str(v).strip()})
        ]

    if from_date or to_date:
        skills_timeline = [e for e in skills_timeline if _date_in_range(_parse_date(_event_ts(e)), from_date, to_date)]
        projects = [p for p in projects if _date_in_range(_parse_date(p.get("created_at")), from_date, to_date)]
        top_project_evolution = [
            row for row in top_project_evolution if _date_in_range(_parse_date(row.get("created_at")), from_date, to_date)
        ]
        activity_heatmap = [
            bucket
            for bucket in activity_heatmap
            if _date_in_range(_parse_date(bucket.get("bucket_date")), from_date, to_date)
        ]

    if text_query:
        projects = [p for p in projects if _contains_text([p.get("name"), p.get("display_name")], text_query)]
        top_projects = [p for p in top_projects if _contains_text([p.get("project_name"), p.get("name")], text_query)]
        skills_timeline = [
            event
            for event in skills_timeline
            if _contains_text([event.get("skill"), event.get("project_name")], text_query)
        ]
        top_project_evolution = [
            row
            for row in top_project_evolution
            if _contains_text([row.get("project_name"), row.get("evolution_summary")], text_query)
        ]
        showcases = [
            row
            for row in showcases
            if _contains_text(
                [
                    row.get("project_name"),
                    (row.get("content") or {}).get("title"),
                    (row.get("content") or {}).get("summary_text"),
                ],
                text_query,
            )
        ]

    sort = str(filters.get("sort") or DEFAULT_PUBLIC_SORT).strip().lower()
    projects = _sort_rows(projects, sort=sort, id_key="id", name_key="name", date_key="created_at", score_key="metrics.rank_score")
    top_projects = _sort_rows(
        top_projects,
        sort=sort,
        id_key="project_id",
        name_key="project_name",
        date_key="created_at",
        score_key="rank_score",
    )
    top_project_evolution = _sort_rows(
        top_project_evolution,
        sort=sort,
        id_key="project_id",
        name_key="project_name",
        date_key="created_at",
        score_key="rank_score",
    )
    skills_timeline = sorted(
        skills_timeline,
        key=lambda row: (
            _sort_ts(_parse_date(_event_ts(row))),
            str(row.get("skill") or ""),
            str(row.get("project_id") or ""),
        ),
    )
    if sort in {"date_desc", "rank_desc", "name_desc"}:
        skills_timeline = list(reversed(skills_timeline))

    if "projects" in source:
        source["projects"] = projects
    if "top_projects" in source:
        source["top_projects"] = top_projects
    if "skills_timeline" in source:
        source["skills_timeline"] = skills_timeline
    if "activity_heatmap" in source:
        source["activity_heatmap"] = activity_heatmap
    if "showcases" in source:
        source["showcases"] = showcases
    return source


def _parse_multi_value(query_params: Any, key: str, casefold: bool = False) -> List[str]:
    values: List[str] = []
    if hasattr(query_params, "getlist"):
        values.extend([str(v) for v in (query_params.getlist(key) or []) if str(v).strip()])
    else:
        raw = query_params.get(key)
        if raw is None:
            return []
        values.append(str(raw))

    out: List[str] = []
    seen: Set[str] = set()
    for raw in values:
        for token in str(raw).split(","):
            item = token.strip()
            if not item:
                continue
            normalized = item.casefold() if casefold else item
            if normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized if casefold else item)
    return out


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        if len(text_value) == 10:
            return date.fromisoformat(text_value)
        return datetime.fromisoformat(text_value.replace("Z", "+00:00")).date()
    except Exception as exc:
        raise ValueError(f"Invalid ISO date value: {text_value}") from exc


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _public_username(*, display_name: Any) -> str:
    name = str(display_name or "").strip()
    if name:
        return name

    return "User"


def _json_dump(value: Any) -> str:
    import json

    return json.dumps(value or {}, default=str)


def _ensure_rows(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in value:
        if isinstance(row, dict):
            out.append(dict(row))
    return out


def _contains_text(candidates: Sequence[Any], query_cf: str) -> bool:
    for value in candidates:
        if query_cf in str(value or "").casefold():
            return True
    return False


def _event_ts(event: Mapping[str, Any]) -> Any:
    return event.get("first_seen_ts") or event.get("timestamp")


def _date_in_range(value: Optional[date], date_from: Optional[date], date_to: Optional[date]) -> bool:
    if value is None:
        return not date_from and not date_to
    if date_from and value < date_from:
        return False
    if date_to and value > date_to:
        return False
    return True


def _sort_ts(value: Optional[date]) -> int:
    if value is None:
        return -1
    return int(value.strftime("%Y%m%d"))


def _nested_value(row: Mapping[str, Any], dotted_key: str) -> Any:
    current: Any = row
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _sort_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    sort: str,
    id_key: str,
    name_key: str,
    date_key: str,
    score_key: str,
) -> List[Dict[str, Any]]:
    sorted_rows = list(rows)

    if sort in {"rank_desc", "rank_asc"}:
        reverse = sort == "rank_desc"
        sorted_rows.sort(
            key=lambda row: (
                _coerce_float(_nested_value(row, score_key)),
                str(row.get(name_key) or ""),
                str(row.get(id_key) or ""),
            ),
            reverse=reverse,
        )
        return sorted_rows

    if sort in {"name_asc", "name_desc"}:
        reverse = sort == "name_desc"
        sorted_rows.sort(
            key=lambda row: (
                str(row.get(name_key) or "").casefold(),
                str(row.get(id_key) or ""),
            ),
            reverse=reverse,
        )
        return sorted_rows

    reverse = sort == "date_desc"
    sorted_rows.sort(
        key=lambda row: (
            _sort_ts(_parse_date(row.get(date_key))),
            str(row.get(name_key) or "").casefold(),
            str(row.get(id_key) or ""),
        ),
        reverse=reverse,
    )
    return sorted_rows


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("-inf")
