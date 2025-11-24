# tests/test_identify_projects.py
import os
import sys
from unittest.mock import patch, Mock

import pytest

# Make sure we can import from src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from collaborative import identify_projects as ip


# ---------- _normalize_name ----------

def test_normalize_name_basic_and_unicode():
    assert ip._normalize_name("  JOHN  ") == "john"
    # Casefold + Unicode: É → é
    assert ip._normalize_name(" Éva ") == "éva"
    # NFKC normalization (wide chars etc.)
    assert ip._normalize_name("Ａｌｅｘ") == "alex"


# ---------- _letters_only_unicode ----------

def test_letters_only_unicode_keeps_letters_and_name_punct():
    s = "Jean-Claude O'Neill 123!?"
    assert ip._letters_only_unicode(s) == "Jean-Claude O'Neill"

def test_letters_only_unicode_keeps_nonlatin_scripts():
    # Arabic with digits/punct that should be stripped
    s = "محمد-علي 123!"
    assert ip._letters_only_unicode(s) == "محمد-علي"

def test_is_top_common_name_handles_multiword(monkeypatch):
    # If you want multi-word acceptance, ensure the joined token exists
    # Here we only test single-token pass-through; filename splitting happens elsewhere
    monkeypatch.setattr(ip, "TOP_FIRST_SET", {"jean", "claude"}, raising=False)
    monkeypatch.setattr(ip, "TOP_LAST_SET", set(), raising=False)
    # Only single tokens are passed here; multi-word splitting is tested below
    assert ip.is_top_common_name("jean") == "Jean"
    assert ip.is_top_common_name("claude") == "Claude"


# ---------- _count_git_files ----------

def test_count_git_files_counts_git_dirs_and_root_configs():
    files = [
        {"file_path": "proj/.git/config", "file_name": "config"},
        {"file_path": ".git/HEAD", "file_name": "HEAD"},
        {"file_path": "proj/src/app.py", "file_name": ".gitattributes"},
        {"file_path": "proj/README.md", "file_name": "README.md"},
        {"file_path": "proj/.github/workflows/ci.yml", "file_name": "ci.yml"},
        {"file_path": "proj", "file_name": ".gitmodules"},
        {"file_path": "proj/notes.txt", "file_name": ".gitignore"},
    ]
    # Should count: /.git/ entries + .gitattributes + .gitmodules + .gitignore => 5
    assert ip._count_git_files(files) == 5


# ---------- _detect_team_structure ----------

def test_detect_team_structure_true_when_indicators_present():
    files = [
        {"file_name": "main.py"},
        {"file_name": "TEAM_utils.py"},
        {"file_name": "shared_config.py"},
        {"file_name": "notes.txt"},
    ]
    assert ip._detect_team_structure(files) is True

def test_detect_team_structure_false_when_absent():
    files = [
        {"file_name": "main.py"},
        {"file_name": "readme.md"},
        {"file_name": "notes.txt"},
    ]
    assert ip._detect_team_structure(files) is False


# ---------- _extract_common_names_from_filenames ----------

def test_extract_common_names_from_filenames(monkeypatch):
    # Make name detection deterministic
    monkeypatch.setattr(ip, "TOP_FIRST_SET", {"john", "mary"}, raising=False)
    monkeypatch.setattr(ip, "TOP_LAST_SET", {"lee"}, raising=False)

    files = [
        {"file_name": "john_report.txt"},
        {"file_name": "mary-ann_notes.md"},
        {"file_name": "LEE_summary.pdf"},
        {"file_name": "misc.txt"},
        {"file_name": "Mary_John-Lee.png"},
    ]
    names = ip._extract_common_names_from_filenames(files)
    # Title-cased in results
    assert names.issuperset({"John", "Mary", "Lee"})


# ---------- _identify_authors_from_zip ----------

def test_identify_authors_from_zip_returns_empty_when_invalid_project_id():
    assert ip._identify_authors_from_zip(0) == set()
    assert ip._identify_authors_from_zip(-5) == set()

@patch("collaborative.identify_projects.get_zip_file")
def test_identify_authors_from_zip_no_zip(mock_get_zip):
    mock_get_zip.return_value = None
    assert ip._identify_authors_from_zip(123) == set()

@patch("collaborative.identify_projects.identify_contributors")
@patch("collaborative.identify_projects.get_zip_file")
def test_identify_authors_from_zip_happy_path(mock_get_zip, mock_identify):
    mock_get_zip.return_value = b"fake-zip-bytes"

    fake_ic = Mock()
    fake_ic.extract_repo.return_value = "/tmp/repo"
    fake_ic.get_commit_counts.return_value = {
        "Alice <alice@example.com>": 7,
        "Bob <bob@example.com>": 3,
    }
    fake_ic.cleanup.return_value = None
    mock_identify.return_value = fake_ic

    authors = ip._identify_authors_from_zip(999)
    assert authors == {"Alice <alice@example.com>", "Bob <bob@example.com>"}
    fake_ic.extract_repo.assert_called_once()
    fake_ic.get_commit_counts.assert_called_once()
    fake_ic.cleanup.assert_called_once()

@patch("collaborative.identify_projects.identify_contributors", side_effect=RuntimeError("boom"))
@patch("collaborative.identify_projects.get_zip_file", return_value=b"bytes")
def test_identify_authors_from_zip_handles_exception(_mock_get_zip, _mock_identify):
    # Should swallow exception and return empty set
    assert ip._identify_authors_from_zip(5) == set()


# ---------- _compute_collab_score ----------

def test_compute_collab_score_various_combinations():
    # No signals
    ind = {"git_files": 0, "team_structure": False, "has_common_names": False}
    assert ip._compute_collab_score(ind, set()) == 0

    # Git only
    ind = {"git_files": 1, "team_structure": False, "has_common_names": False}
    assert ip._compute_collab_score(ind, {"Solo"}) == 50

    # Team indicator only
    ind = {"git_files": 0, "team_structure": True, "has_common_names": False}
    assert ip._compute_collab_score(ind, {"Solo"}) == 25

    # Multiple authors only
    ind = {"git_files": 0, "team_structure": False, "has_common_names": False}
    assert ip._compute_collab_score(ind, {"A", "B"}) == 50

    # Git + team
    ind = {"git_files": 1, "team_structure": True, "has_common_names": False}
    assert ip._compute_collab_score(ind, {"Solo"}) == 75  # 50 + 25

    # Git + team + multi-authors (cap at 100)
    ind = {"git_files": 1, "team_structure": True, "has_common_names": False}
    assert ip._compute_collab_score(ind, {"A", "B"}) == 100

    # Has common names
    ind = {"git_files": 0, "team_structure": False, "has_common_names": True}
    assert ip._compute_collab_score(ind, set()) == 40
