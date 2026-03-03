from __future__ import annotations

import re
import secrets
from typing import Any, Dict, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

DASHBOARD_MODE_PRIVATE = "private"
DASHBOARD_MODE_PUBLIC = "public"
ALLOWED_DASHBOARD_MODES = {DASHBOARD_MODE_PRIVATE, DASHBOARD_MODE_PUBLIC}


def _to_dashboard_out(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "portfolio_id": str(row.get("portfolio_id")),
        "mode": str(row.get("mode") or DASHBOARD_MODE_PRIVATE),
        "public_slug": str(row.get("public_slug") or ""),
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
            SELECT portfolio_id, mode, public_slug, active_publication_id, published_at, created_at, updated_at
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
        slug = _slug_candidate()
        conn.execute(
            text(
                """
                INSERT INTO portfolio_dashboards (portfolio_id, mode, public_slug)
                VALUES (:pid, :mode, :slug)
                ON CONFLICT DO NOTHING
                """
            ),
            {"pid": portfolio_id, "mode": DASHBOARD_MODE_PRIVATE, "slug": slug},
        )
        row = conn.execute(
            text(
                """
                SELECT portfolio_id, mode, public_slug, active_publication_id, published_at, created_at, updated_at
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


def regenerate_portfolio_public_slug(conn, portfolio_id: str) -> Dict[str, Any]:
    ensure_portfolio_dashboard(conn, portfolio_id)

    for _ in range(10):
        slug = _slug_candidate()
        try:
            conn.execute(
                text(
                    """
                    UPDATE portfolio_dashboards
                    SET public_slug = :slug, updated_at = NOW()
                    WHERE portfolio_id = :pid
                    """
                ),
                {"pid": portfolio_id, "slug": slug},
            )
            return ensure_portfolio_dashboard(conn, portfolio_id)
        except IntegrityError:
            continue

    raise RuntimeError("Unable to generate a unique public slug")
