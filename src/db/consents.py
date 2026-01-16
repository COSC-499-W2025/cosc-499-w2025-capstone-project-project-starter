from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def get_snapshot_owner_user_id(conn: Connection, snapshot_id: str) -> Optional[str]:
    """
    Resolve the owning user_id for a snapshot via:
      snapshots -> projects -> portfolios -> users
    """
    return conn.execute(
        text(
            """
            SELECT pf.user_id
            FROM snapshots s
            JOIN projects pr ON pr.id = s.project_id
            JOIN portfolios pf ON pf.id = pr.portfolio_id
            WHERE s.id = :sid
            """
        ),
        {"sid": snapshot_id},
    ).scalar()


def latest_consent_granted(conn: Connection, user_id: str, consent_type: str) -> Optional[bool]:
    """
    Returns latest granted state for consent_type, or None if no records exist.
    """
    return conn.execute(
        text(
            """
            SELECT granted
            FROM privacy_consents
            WHERE user_id = :uid AND consent_type = :ctype
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"uid": user_id, "ctype": consent_type},
    ).scalar()


def is_external_services_allowed(conn: Connection, user_id: str) -> bool:
    """
    External services are allowed only if the latest consent record exists and is granted.
    """
    return latest_consent_granted(conn, user_id, "external_services") is True


def is_data_access_allowed(conn: Connection, user_id: str) -> bool:
    return latest_consent_granted(conn, user_id, "data_access") is True


def snapshot_external_services_allowed(engine: Engine, snapshot_id: str) -> bool:
    with engine.connect() as conn:
        uid = get_snapshot_owner_user_id(conn, snapshot_id)
        if not uid:
            return False
        return is_external_services_allowed(conn, str(uid))
