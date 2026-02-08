from __future__ import annotations

import os
from typing import Optional

from src.config.config_manager import UserConfigManager
from src.insights.storage import DEFAULT_DB_PATH, ProjectInsightsStore
from src.insights.user_role_store import ProjectRoleStore


def resolve_db_path(db_url: Optional[str] = None) -> str:
    env_url = os.getenv("DATABASE_URL")
    effective = db_url or env_url or f"sqlite:///{DEFAULT_DB_PATH}"
    return effective.replace("sqlite:///", "")


def get_store(db_url: Optional[str] = None) -> ProjectInsightsStore:
    db_path = resolve_db_path(db_url)
    return ProjectInsightsStore(db_path=db_path)


def get_config_manager(db_url: Optional[str] = None) -> UserConfigManager:
    db_path = resolve_db_path(db_url)
    return UserConfigManager(db_path=db_path)


def get_role_store(db_url: Optional[str] = None) -> ProjectRoleStore:
    db_path = resolve_db_path(db_url)
    return ProjectRoleStore(db_path=db_path)
