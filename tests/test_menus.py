import os
import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Make src importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import cli.menus as menus  # noqa: E402


@patch("cli.menus.select_project_interactive", return_value={"id": 7, "filename": "demo.zip"})
@patch("cli.menus.analyze_project_by_id")
@patch("builtins.input", return_value="q")
@patch("sys.stdout", new_callable=StringIO)
def test_analyze_project_menu_runs_analysis(mock_stdout, mock_input, mock_analyze, mock_select):
    """Ensure analyze_project_menu prompts and triggers analysis when a project is chosen."""
    menus.analyze_project_menu()

    output = mock_stdout.getvalue()
    assert "Analyzing: demo.zip" in output
    assert "PRIVACY MODE" in output
    mock_analyze.assert_called_once_with(7)
    mock_select.assert_called_once()


@patch("cli.menus.ExternalServicePermission")
@patch("builtins.input", return_value="1")
@patch("sys.stdout", new_callable=StringIO)
def test_manage_external_services_view_status(mock_stdout, mock_input, mock_perm_cls):
    """View status branch should query permission manager and display status."""
    mock_perm = mock_perm_cls.return_value
    mock_perm.has_permission.return_value = True

    menus.manage_external_services_menu()

    output = mock_stdout.getvalue()
    assert "External Service Settings" in output
    assert "permission GRANTED" in output
    mock_perm.has_permission.assert_called_once_with("LLM")


@patch("cli.menus.ExternalServicePrompt.store_permission")
@patch("builtins.input", side_effect=["3", "yes"])
@patch("sys.stdout", new_callable=StringIO)
def test_manage_external_services_revoke(mock_stdout, mock_input, mock_store):
    """Revoke branch should call store_permission when user confirms."""
    menus.manage_external_services_menu()

    output = mock_stdout.getvalue()
    assert "permission has been REVOKED" in output
    mock_store.assert_called_once_with("default_user", "LLM", False)


def test_ask_user_preferences_existing_prefs_and_username_change_prompt():
    """When prefs already exist, ensure collaborative opt out and username change prompts run."""

    class DummyConsent:
        def __init__(self):
            self.withdrawn = False

        def has_access(self):
            return True

        def withdraw(self):
            self.withdrawn = True

        def request_consent_if_needed(self):
            pass

    class DummyCollab:
        def __init__(self):
            self.updated_value = None

        def get_preferences(self):
            return ("user", True)

        def update_collaborative(self, value):
            self.updated_value = value

    consent = DummyConsent()
    collab = DummyCollab()

    inputs = ["no", "maybe", "yes", "no"]  # withdraw?, invalid collab response, opt out, skip username change
    with patch("builtins.input", side_effect=inputs), patch(
        "cli.menus.get_user_git_username", return_value="existing_user"
    ), patch("cli.menus.update_user_git_username") as mock_update, patch("sys.stdout", new_callable=StringIO):
        menus.ask_user_preferences(consent, collab, is_start=False)

    assert collab.updated_value is False
    mock_update.assert_not_called()
    assert consent.withdrawn is False


def test_ask_user_preferences_collaborative_flow_repo_missing():
    """When collaborative is granted but repo extraction fails, function should return early."""

    class DummyConsent:
        def has_access(self):
            return False

        def request_consent_if_needed(self):
            return True

    class DummyCollab:
        def get_preferences(self):
            return None

        def request_collaborative_if_needed(self):
            return True

    mock_ic = MagicMock()
    mock_ic.extract_repo.return_value = None

    with patch("builtins.input", side_effect=["newuser"]), patch(
        "cli.menus.identify_contributors", return_value=mock_ic
    ), patch(
        "cli.menus.get_user_git_username", side_effect=[None, "newuser"]
    ), patch("cli.menus.update_user_git_username") as mock_update, patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        menus.ask_user_preferences(DummyConsent(), DummyCollab(), is_start=False)

    assert "github username is:newuser" in mock_stdout.getvalue()
    mock_update.assert_called_once_with("newuser")


@patch("cli.menus.list_projects_menu")
def test_handle_list_projects_calls_display(mock_list_projects):
    """handle_list_projects should delegate to list_projects_menu."""
    menus.handle_list_projects()
    mock_list_projects.assert_called_once()


@patch("cli.menus.display_success")
@patch("upload_file.add_file_to_db")
@patch("builtins.input", return_value="/tmp/data.zip")
def test_handle_upload_file_success(mock_input, mock_add_file, mock_display_success):
    """handle_upload_file should call display_success when upload succeeds."""
    mock_add_file.return_value = SimpleNamespace(success=True)
    menus.handle_upload_file()
    mock_display_success.assert_called_once()


@patch("cli.menus.AuthManager")
@patch("cli.menus.display_success")
@patch("upload_file.add_thumbnail_to_project")
@patch("builtins.input", return_value="/tmp/thumb.png")
@patch("cli.menus.select_project_interactive", return_value={"id": 3, "filename": "demo.zip"})
def test_handle_add_project_thumbnail_success(mock_select, mock_input, mock_add_thumb, mock_display_success):
    """handle_add_project_thumbnail should save thumbnail and show success."""
    mock_add_thumb.return_value = SimpleNamespace(success=True)
    menus.handle_add_project_thumbnail()
    mock_add_thumb.assert_called_once_with(3, "/tmp/thumb.png")
    mock_display_success.assert_called_once()


#@patch("upload_file.add_thumbnail_to_project")
#@patch("cli.menus.select_project_interactive", return_value=None)
#def test_handle_add_project_thumbnail_no_selection(mock_select, mock_add_thumb):
    #"""No selection should exit early without saving."""
    #menus.handle_add_project_thumbnail()
    #mock_add_thumb.assert_not_called()


@patch("cli.menus.summarize_project", return_value="summary text")
@patch("cli.menus.analyze_project_from_db")
@patch("cli.menus.select_project_interactive", return_value={"id": 1, "filename": "file.py"})
@patch("builtins.input", return_value="")
@patch("sys.stdout", new_callable=StringIO)
def test_handle_analyze_metrics_and_summary(mock_stdout, mock_input, mock_select, mock_analyze, mock_summary, mock_auth):
    """Combined metrics+summary flow should analyze and print summary."""
    # Mock AuthManager to return a valid username
    mock_auth.get_current_username.return_value = 'test_user'
    
    menus.handle_analyze_metrics_and_summary()

    output = mock_stdout.getvalue()
    assert "FULL (metrics + summary)" in output
    mock_analyze.assert_called_once_with(1)
    # Verify summarize_project called with user_name parameter
    mock_summary.assert_called_once_with(1, user_name='test_user')


@patch("cli.menus.AuthManager")
@patch("cli.menus.save_rankings_with_summaries")
@patch("cli.menus.display_rankings")
@patch("cli.menus.rank_all_projects", return_value=[{"id": 1}])
@patch("builtins.input", side_effect=["y", "n", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_handle_rank_projects_save_flow(mock_stdout, mock_input, mock_rank, mock_display, mock_save, mock_auth):
    """Ranking flow should optionally save rankings based on user input."""
    # Mock AuthManager to return a valid username
    mock_auth.get_current_username.return_value = 'test_user'
    
    menus.handle_rank_projects()

    # Verify rank_all_projects called with user_name parameter
    mock_rank.assert_called_once_with(user_name='test_user')
    mock_display.assert_called_once()
    mock_save.assert_called_once_with([{"id": 1}], False)
    assert "Ranking all projects" in mock_stdout.getvalue()


@patch("cli.menus.AuthManager")
@patch("cli.menus.save_rankings_with_summaries")
@patch("cli.menus.rank_all_projects", return_value=[{"id": 2}])
@patch("cli.menus.rank_and_summarize_top_projects")
@patch("builtins.input", side_effect=["y", "y", ""])
def test_handle_rank_and_summarize_projects(mock_input, mock_rank_and_summarize, mock_rank_all, mock_save, mock_auth):
    """Rank and summarize flow should save when user opts in."""
    # Mock AuthManager to return a valid username
    mock_auth.get_current_username.return_value = 'test_user'
    
    menus.handle_rank_and_summarize_projects()

    mock_rank_and_summarize.assert_called_once()
    # Verify rank_all_projects called with user_name parameter
    mock_rank_all.assert_called_once_with(user_name='test_user')
    mock_save.assert_called_once_with([{"id": 2}], True)


@patch("cli.menus.update_ranking_position", return_value=True)
@patch("cli.menus.update_ranking_summary", return_value=True)
@patch("cli.menus.update_ranking_score", return_value=True)
@patch(
    "cli.menus.get_stored_ranking_by_project_id",
    return_value={
        "project_id": 10,
        "rank_position": 1,
        "score": 9.0,
        "created_at": "today",
        "updated_at": "today",
        "summary": "Existing",
    },
)
@patch("cli.menus.get_stored_rankings", return_value=[{"rank_position": 1, "project_id": 10, "score": 9.0, "ranking_data": {"filename": "example"}, "summary": "Existing"}])
@patch(
    "builtins.input",
    side_effect=[
        "1",
        "10",  # view details
        "2",
        "10",
        "9.5",  # edit score
        "3",
        "10",
        "Updated summary",
        "",  # end summary input
        "4",
        "10",
        "2",  # change rank
        "5",
    ],
)
@patch("sys.stdout", new_callable=StringIO)
def test_handle_view_edit_rankings_full_loop(
    mock_stdout,
    mock_input,
    mock_get_rankings,
    mock_get_by_id,
    mock_update_score,
    mock_update_summary,
    mock_update_position,
):
    """Exercise the edit rankings menu through multiple options."""
    menus.handle_view_edit_rankings()

    out = mock_stdout.getvalue()
    assert "VIEW AND EDIT STORED RANKINGS" in out
    assert "Successfully updated score" in out
    assert "Successfully updated summary" in out
    assert "Successfully updated rank position" in out


@patch("cli.menus.delete_insights", return_value=(1, 1, 1))
@patch("builtins.input", side_effect=["42", "y"])
@patch("sys.stdout", new_callable=StringIO)
def test_handle_cleanup_insights_confirms_and_deletes(mock_stdout, mock_input, mock_delete):
    """cleanup menu should call delete_insights when user confirms."""
    menus.handle_cleanup_insights()
    mock_delete.assert_called_once_with(42)
    assert "Deleted: project_metrics=1" in mock_stdout.getvalue()


@patch("portfolio.portfolio_display.portfolio_menu")
def test_portfolio_menu_delegates(mock_portfolio_menu):
    """portfolio_menu wrapper should forward call to portfolio.portfolio_display.portfolio_menu."""
    menus.portfolio_menu()
    mock_portfolio_menu.assert_called_once()


@patch("account.user_manager.AuthManager.get_current_user")
@patch("account.user_manager.AuthManager.is_user_logged_in")
@patch("resume.resume_manager.ResumeManager.delete_user_resume", return_value=True)
@patch("resume.resume_manager.ResumeManager.resume_exists", return_value=True)
@patch("builtins.input", side_effect=["y", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_handle_delete_resume_success(mock_stdout, mock_input, mock_exists, mock_delete, mock_is_logged_in, mock_get_user):
    """handle_delete_resume should delete when confirmed."""
    # Mock logged in user
    mock_is_logged_in.return_value = True
    mock_get_user.return_value = {'user_name': 'test_user'}
    
    menus.handle_delete_resume()
    mock_delete.assert_called_once_with("test_user")
    assert "Resume deleted successfully" in mock_stdout.getvalue()


@patch("account.user_manager.AuthManager.get_current_user")
@patch("account.user_manager.AuthManager.is_user_logged_in")
@patch("resume.resume_manager.ResumeManager.get_user_resume", return_value=None)
@patch("resume.resume_manager.ResumeManager.resume_exists", return_value=True)
@patch("builtins.input", return_value="")
@patch("sys.stdout", new_callable=StringIO)
def test_handle_view_resume_missing_record(mock_stdout, mock_input, mock_exists, mock_get_resume, mock_is_logged_in, mock_get_user):
    """Gracefully handle missing resume record."""
    # Mock logged in user
    mock_is_logged_in.return_value = True
    mock_get_user.return_value = {'user_name': 'test_user'}
    
    menus.handle_view_resume()
    assert "Failed to retrieve resume" in mock_stdout.getvalue()


@patch("account.user_manager.AuthManager.get_current_user")
@patch("account.user_manager.AuthManager.is_user_logged_in")
@patch("resume.resume_formatter.ResumeFormatter.get_formatted_resume", return_value=None)
@patch(
    "resume.resume_manager.ResumeManager.get_user_resume",
    return_value={"resume_data": {"name": "User", "all_skills": [], "total_projects_analyzed": 0, "top_projects_displayed": 0}},
)
@patch("resume.resume_manager.ResumeManager.resume_exists", return_value=True)
@patch("builtins.input", side_effect=["2", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_handle_view_resume_format_failure(mock_stdout, mock_input, mock_exists, mock_get_resume, mock_format_resume, mock_is_logged_in, mock_get_user):
    """If formatting fails, an error message should be shown."""
    # Mock logged in user
    mock_is_logged_in.return_value = True
    mock_get_user.return_value = {'user_name': 'test_user'}
    
    menus.handle_view_resume()
    assert "Failed to format resume" in mock_stdout.getvalue()


@patch("resume.resume_formatter.ResumeFormatter.format_pdf", return_value=True)
@patch("builtins.input", return_value="")
@patch("sys.stdout", new_callable=StringIO)
def test_handle_pdf_export_uses_default_filename(mock_stdout, mock_input, mock_format_pdf):
    """_handle_pdf_export should append .pdf and call formatter."""
    menus._handle_pdf_export({"sample": "data"})

    output = mock_stdout.getvalue()
    assert "resume.pdf" in output
    mock_format_pdf.assert_called_once()
