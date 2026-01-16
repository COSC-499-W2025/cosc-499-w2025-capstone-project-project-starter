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

def _deep_merge(base: Any, patch: Any) -> Any:
    """
    Recursive, dict-only merge.
    - dict + dict => recurse per key
    - otherwise => patch replaces base
    This is the behavior required by PATCH semantics in tests.
    """
    if isinstance(base, dict) and isinstance(patch, dict):
        out: Dict[str, Any] = dict(base)
        for k, v in patch.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out
    return patch


def _normalize_config(cfg: Any) -> Dict[str, Any]:
    """
    Enforce a stable shape, but do not derive/auto-populate values from other tables.
    """
    if not isinstance(cfg, dict):
        cfg = {}

    # Start from DEFAULT_CONFIG so required top-level keys always exist.
    out: Dict[str, Any] = _deep_merge(DEFAULT_CONFIG, dict(cfg))

    # identity defaults + normalization
    identity = out.get("identity")
    if not isinstance(identity, dict):
        identity = {}
    identity_out: Dict[str, Any] = dict(identity)

    me = identity_out.get("match_emails")
    if not isinstance(me, list):
        me = []
    identity_out["match_emails"] = [str(x) for x in me if str(x).strip()]

    mn = identity_out.get("match_names")
    if not isinstance(mn, list):
        mn = []
    identity_out["match_names"] = [str(x) for x in mn if str(x).strip()]

    pcm = identity_out.get("project_contributor_map")
    if not isinstance(pcm, dict):
        pcm = {}
    identity_out["project_contributor_map"] = {str(k): str(v) for k, v in pcm.items()}

    out["identity"] = identity_out

    # ranking defaults + normalization (reserved for milestone 2, must be a dict)
    ranking = out.get("ranking")
    if not isinstance(ranking, dict):
        ranking = {}
    out["ranking"] = dict(ranking)

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
    Deep merge in Python, then persist as JSONB.
    Avoid Postgres `||` shallow merge (it overwrites nested dicts like identity).
    """
    ensure_user_config_row(conn, user_id)

    current = conn.execute(
        text("SELECT config_json FROM user_config WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar_one()

    merged = _deep_merge(_normalize_config(current), patch if isinstance(patch, dict) else {})
    merged_norm = _normalize_config(merged)

    conn.execute(
        text(
            """
            UPDATE user_config
            SET config_json = CAST(:cfg AS jsonb),
                updated_at = NOW()
            WHERE user_id = :uid
            """
        ),
        {"uid": user_id, "cfg": json.dumps(merged_norm)},
    )

    return merged_norm

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
