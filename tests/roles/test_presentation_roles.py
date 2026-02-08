import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.project.presentation_roles import (
    generate_portfolio_item_with_role,
    generate_resume_item_with_role,
)


def test_presentation_roles_include_user_role_when_set():
    project_dict = {"project_name": "Role Project", "user_role": "Lead Developer"}

    portfolio = generate_portfolio_item_with_role(project_dict)
    resume = generate_resume_item_with_role(project_dict)

    assert portfolio["user_role"] == "Lead Developer"
    assert resume["user_role"] == "Lead Developer"


def test_presentation_roles_omit_user_role_when_missing():
    project_dict = {"project_name": "Roleless Project"}

    portfolio = generate_portfolio_item_with_role(project_dict)
    resume = generate_resume_item_with_role(project_dict)

    assert "user_role" not in portfolio
    assert "user_role" not in resume
