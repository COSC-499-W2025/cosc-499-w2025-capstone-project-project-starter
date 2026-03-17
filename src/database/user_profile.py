"""User profile for resume (display name, email, education). Shown on first login."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from config.db_config import with_db_cursor


def init_user_profile_table():
    """Create user_profile table if it doesn't exist."""
    with with_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_name VARCHAR(255) PRIMARY KEY,
                display_name VARCHAR(500),
                email VARCHAR(500),
                education JSONB DEFAULT '[]'::jsonb,
                linkedin VARCHAR(500),
                github VARCHAR(500),
                phone VARCHAR(100),
                website VARCHAR(500),
                summary TEXT,
                location VARCHAR(500),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS github VARCHAR(500);")
        cursor.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS phone VARCHAR(100);")
        cursor.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS website VARCHAR(500);")
        cursor.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS summary TEXT;")
        cursor.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS location VARCHAR(500);")


def get_profile(user_name: str) -> Optional[Dict[str, Any]]:
    """Get profile for user. Returns None if no row or all fields empty."""
    with with_db_cursor() as cursor:
        cursor.execute(
            """SELECT display_name, email, education, linkedin, github, phone, website, summary, location
               FROM user_profile WHERE user_name = %s""",
            (user_name,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    display_name = row[0]
    email = row[1]
    education = row[2]
    linkedin = row[3] if len(row) > 3 else None
    github = row[4] if len(row) > 4 else None
    phone = row[5] if len(row) > 5 else None
    website = row[6] if len(row) > 6 else None
    summary = row[7] if len(row) > 7 else None
    location = row[8] if len(row) > 8 else None
    if not display_name and not email and not education and not linkedin and not github and not phone and not website and not summary and not location:
        return None
    edu = education
    if isinstance(edu, str):
        try:
            edu = json.loads(edu) if edu else []
        except Exception:
            edu = []
    return {
        "display_name": display_name or "",
        "email": email or "",
        "education": edu if isinstance(edu, list) else [],
        "linkedin": linkedin or "",
        "github": github or "",
        "phone": phone or "",
        "website": website or "",
        "summary": summary or "",
        "location": location or "",
    }


def save_profile(
    user_name: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    education: Optional[List[Dict[str, Any]]] = None,
    linkedin: Optional[str] = None,
    github: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    summary: Optional[str] = None,
    location: Optional[str] = None,
) -> bool:
    """Save or update profile. None values leave existing fields unchanged."""
    with with_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO user_profile (user_name, display_name, email, education, linkedin, github, phone, website, summary, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_name) DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, user_profile.display_name),
                email = COALESCE(EXCLUDED.email, user_profile.email),
                education = COALESCE(EXCLUDED.education, user_profile.education),
                linkedin = COALESCE(EXCLUDED.linkedin, user_profile.linkedin),
                github = COALESCE(EXCLUDED.github, user_profile.github),
                phone = COALESCE(EXCLUDED.phone, user_profile.phone),
                website = COALESCE(EXCLUDED.website, user_profile.website),
                summary = COALESCE(EXCLUDED.summary, user_profile.summary),
                location = COALESCE(EXCLUDED.location, user_profile.location),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_name,
                display_name or None,
                email or None,
                json.dumps(education) if education is not None else None,
                linkedin or None,
                github or None,
                phone or None,
                website or None,
                summary or None,
                location or None,
            ),
        )
    return True
