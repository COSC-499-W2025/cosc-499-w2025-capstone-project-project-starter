"""
presentation_roles.py
---------------------
Helpers to include user_role in portfolio and resume outputs without
modifying the core presentation module.
"""

from __future__ import annotations

from typing import Any, Dict

from .presentation import generate_portfolio_item, generate_resume_item


def generate_portfolio_item_with_role(project_dict: Dict[str, Any]) -> Dict[str, Any]:
    item = generate_portfolio_item(project_dict)
    user_role = project_dict.get("user_role")
    if isinstance(user_role, str) and user_role.strip():
        item = dict(item)
        item["user_role"] = user_role.strip()
    return item


def generate_resume_item_with_role(project_dict: Dict[str, Any]) -> Dict[str, Any]:
    item = generate_resume_item(project_dict)
    user_role = project_dict.get("user_role")
    if isinstance(user_role, str) and user_role.strip():
        item = dict(item)
        item["user_role"] = user_role.strip()
    return item
