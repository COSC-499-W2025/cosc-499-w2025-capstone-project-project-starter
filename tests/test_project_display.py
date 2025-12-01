import os
import sys
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest

# Allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import project_display as pd  # noqa: E402


def _project(pid=1, name="demo.zip", created=None):
    return {"id": pid, "filename": name, "created_at": created}


@patch("project_display.get_available_projects", return_value=[])
@patch("sys.stdout", new_callable=StringIO)
def test_select_project_no_projects(mock_stdout, mock_get_projects):
    """Selecting when no projects should return None and show guidance."""
    result = pd.select_project_interactive("Select Project")
    assert result is None
    output = mock_stdout.getvalue()
    assert "No projects found in database." in output
    assert "Please upload a project first" in output


@patch("project_display.get_available_projects", return_value=[_project(1, "one", None)])
@patch("builtins.input", return_value="q")
@patch("sys.stdout", new_callable=StringIO)
def test_select_project_quit(mock_stdout, mock_input, mock_get_projects):
    """User can quit selection with 'q'."""
    result = pd.select_project_interactive("Pick")
    assert result is None
    assert "Available projects:" in mock_stdout.getvalue()


@patch("project_display.get_available_projects", return_value=[_project(1, "one"), _project(2, "two")])
@patch("builtins.input", return_value="2")
@patch("sys.stdout", new_callable=StringIO)
def test_select_project_valid_choice(mock_stdout, mock_input, mock_get_projects):
    """Valid numeric choice returns the selected project."""
    result = pd.select_project_interactive("Pick")
    assert result["id"] == 2
    assert "two" in mock_stdout.getvalue()


@patch("project_display.get_available_projects", return_value=[_project(1, "one", datetime(2024, 1, 1))])
@patch("builtins.input", side_effect=["bad", "1"])
@patch("sys.stdout", new_callable=StringIO)
def test_select_project_invalid_then_valid(mock_stdout, mock_input, mock_get_projects):
    """Invalid input should prompt again until a valid choice is made."""
    result = pd.select_project_interactive("Pick")
    assert result["id"] == 1
    output = mock_stdout.getvalue()
    assert "Please enter a valid number" in output
    assert "2024-01-01" in output


@patch("project_display.list_projects", return_value=[_project(1, "one"), _project(2, "two")])
@patch("builtins.input", return_value="q")
@patch("sys.stdout", new_callable=StringIO)
def test_list_projects_menu_quit(mock_stdout, mock_input, mock_list_projects):
    """List menu should allow quitting without loading files."""
    with patch("project_display.list_project_files") as mock_list_files:
        pd.list_projects_menu()
        mock_list_files.assert_not_called()
    assert "view files" in mock_stdout.getvalue()


@patch("project_display.list_project_files", return_value=["a.py", "b.py"])
@patch("project_display.list_projects", return_value=[_project(1, "one")])
@patch("builtins.input", side_effect=["1", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_list_projects_menu_shows_files(mock_stdout, mock_input, mock_list_projects, mock_list_files):
    """Selecting a project should list its files and total count."""
    pd.list_projects_menu()
    mock_list_files.assert_called_once_with(1)
    output = mock_stdout.getvalue()
    assert "Files in project: one" in output
    assert "Total files: 2" in output


@patch("project_display.list_projects", return_value=[_project(1, "one")])
@patch("builtins.input", return_value="abc")
@patch("sys.stdout", new_callable=StringIO)
def test_list_projects_menu_invalid_value(mock_stdout, mock_input, mock_list_projects):
    """Non-numeric input should be handled gracefully."""
    with patch("project_display.list_project_files") as mock_list_files:
        pd.list_projects_menu()
        mock_list_files.assert_not_called()
    assert "Please enter a valid number" in mock_stdout.getvalue()


@patch("project_display.list_projects", return_value=[_project(1, "one")])
@patch("builtins.input", return_value="5")
@patch("sys.stdout", new_callable=StringIO)
def test_list_projects_menu_out_of_range(mock_stdout, mock_input, mock_list_projects):
    """Out-of-range selection should show guidance."""
    with patch("project_display.list_project_files") as mock_list_files:
        pd.list_projects_menu()
        mock_list_files.assert_not_called()
    assert "Please enter a number between 1 and 1" in mock_stdout.getvalue()

