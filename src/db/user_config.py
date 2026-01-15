from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple, List

from sqlalchemy import text


DEFAULT_CONFIG: Dict[str, Any] = {
    "identity": {
        # global matching rules for auto-linking a contributor to the user.
        "match_emails": [],
        "match_names": [],
        # explicit mapping: project_id -> contributor_id
        # Used both by the API set-user endpoint and by git_metrics auto-linking.
        "project_contributor_map": {},
    },
    "ranking": {
        # Reserved for milestone 2. Current behavior is fixed in code.
    },
}


def _normalize_config(cfg: Any) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        return dict(DEFAULT_CONFIG)
    # Shallow merge defaults to ensure keys exist.
    out = dict(DEFAULT_CONFIG)
    out_identity = dict(DEFAULT_CONFIG.get("identity", {}))
    out_ranking = dict(DEFAULT_CONFIG.get("ranking", {}))

    if isinstance(cfg.get("identity"), dict):
        out_identity.update(cfg["identity"])
    if isinstance(cfg.get("ranking"), dict):
        out_ranking.update(cfg["ranking"])

    out.update(cfg)
    out["identity"] = out_identity
    out["ranking"] = out_ranking

    # Ensure expected types.
    if not isinstance(out["identity"].get("match_emails"), list):
        out["identity"]["match_emails"] = []
    if not isinstance(out["identity"].get("match_names"), list):
        out["identity"]["match_names"] = []
    if not isinstance(out["identity"].get("project_contributor_map"), dict):
        out["identity"]["project_contributor_map"] = {}

    return out


def ensure_user_config_row(conn, user_id: str) -> None:
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


def get_user_config(conn, user_id: str) -> Dict[str, Any]:
    ensure_user_config_row(conn, user_id)
    cfg = conn.execute(
        text("SELECT config_json FROM user_config WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar_one()
    return _normalize_config(cfg)


def put_user_config(conn, user_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ensure_user_config_row(conn, user_id)
    normalized = _normalize_config(cfg)
    conn.execute(
        text(
            """
            UPDATE user_config
            SET config_json = CAST(:cfg AS jsonb),
                updated_at = NOW()
            WHERE user_id = :uid
            """
        ),
        {"uid": user_id, "cfg": json.dumps(normalized)},
    )
    return normalized


def merge_user_config(conn, user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    JSONB merge (shallow) using Postgres `||` operator. Then normalize shape in Python.
    """
    ensure_user_config_row(conn, user_id)
    conn.execute(
        text(
            """
            UPDATE user_config
            SET config_json = (config_json || CAST(:patch AS jsonb)),
                updated_at = NOW()
            WHERE user_id = :uid
            """
        ),
        {"uid": user_id, "patch": json.dumps(patch)},
    )
    return get_user_config(conn, user_id)


def set_project_user_contributor_mapping(conn, user_id: str, project_id: str, contributor_id: str) -> Dict[str, Any]:
    cfg = get_user_config(conn, user_id)
    identity = cfg.setdefault("identity", {})
    m = identity.setdefault("project_contributor_map", {})
    m[str(project_id)] = str(contributor_id)
    return put_user_config(conn, user_id, cfg)


def clear_project_user_contributor_mapping(conn, user_id: str, project_id: str) -> Dict[str, Any]:
    cfg = get_user_config(conn, user_id)
    identity = cfg.setdefault("identity", {})
    m = identity.setdefault("project_contributor_map", {})
    if str(project_id) in m:
        del m[str(project_id)]
    return put_user_config(conn, user_id, cfg)


def resolve_project_owner_user_id(conn, project_id: str) -> Optional[str]:
    """
    projects -> portfolios -> users
    """
    return conn.execute(
        text(
            """
            SELECT p.user_id
            FROM projects pr
            JOIN portfolios p ON p.id = pr.portfolio_id
            WHERE pr.id = :pid
            """
        ),
        {"pid": project_id},
    ).scalar()


def identity_rules_for_user(conn, user_id: str) -> Tuple[List[str], List[str], Dict[str, str]]:
    cfg = get_user_config(conn, user_id)
    ident = cfg.get("identity") or {}
    emails = ident.get("match_emails") or []
    names = ident.get("match_names") or []
    mapping = ident.get("project_contributor_map") or {}
    # Normalize to strings, case-folding is applied by caller.
    emails = [str(x) for x in emails if x]
    names = [str(x) for x in names if x]
    mapping = {str(k): str(v) for k, v in mapping.items() if k and v}
    return emails, names, mapping
