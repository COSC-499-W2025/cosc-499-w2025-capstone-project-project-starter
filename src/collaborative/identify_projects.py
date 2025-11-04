#collaborative/identify_projects.py
from names_dataset import NameDataset
import re
import unicodedata
import re
from typing import Dict, List, Set, Tuple, Any
from parsing.file_contents_manager import get_zip_file
from collaborative.identify_contributors import identify_contributors

nd = NameDataset()
import re
from names_dataset import NameDataset

nd = NameDataset()

def _normalize_name(s: str) -> str:
    # NFKC handles width/compatibility; casefold() for case-insensitive match
    return unicodedata.normalize("NFKC", s).casefold().strip()

# Precompute top lists once (guarded for version differences)
try:
    TOP_FIRST_1000 = nd.get_top_names(n=100, use_first_names=True)
except Exception:
    TOP_FIRST_1000 = set()

try:
    TOP_LAST_500 = nd.get_top_names(n=10, use_first_names=False)
except Exception:
    TOP_LAST_500 = set()

TOP_FIRST_SET = {
    _normalize_name(name)
    for country in TOP_FIRST_1000.values()
    for gender_list in country.values()
    for name in gender_list
}

TOP_LAST_SET = {
    _normalize_name(name)
    for names in TOP_LAST_500.values()
    for name in names

}
    
def _letters_only_unicode(s: str) -> str:
    # Keep all Unicode letters + space/'/’/-
    kept = []
    for ch in s:
        if ch.isalpha() or ch in (" ", "-", "'", "’"):
            kept.append(ch)
    return "".join(kept).strip()

def is_top_common_name(word: str):
    """
    Return title-cased word if it's in the top first/last-name sets; else None.
    Handles Unicode letters, accents, and multi-word names.
    """
    token = _letters_only_unicode(word)
    if not token:
        return None

    key = _normalize_name(token)
    if key in TOP_FIRST_SET or key in TOP_LAST_SET:
        # Title-case heuristically; for better results you could return the canonical
        # form from the dataset instead of .title()
        return token.title()
    return None


def _count_git_files(file_contents: List[Dict[str, Any]]) -> int:
    """Count files indicating a Git repo presence."""
    git_files = 0
    root_git_configs = {'.gitignore', '.gitattributes', '.gitmodules'}
    for fi in file_contents:
        file_path = (fi.get('file_path') or '').lower()
        filename = (fi.get('file_name') or '').lower()
        if "/.git/" in file_path or file_path.startswith(".git/"):
            git_files += 1
        elif filename in root_git_configs:
            git_files += 1
    return git_files



def _detect_team_structure(file_contents: List[Dict[str, Any]]) -> bool:
    """Look for filenames suggesting teamwork."""
    team_indicators = ('team', 'collaborative', 'shared', 'common')
    for fi in file_contents:
        filename = (fi.get('file_name') or '').lower()
        if any(tok in filename for tok in team_indicators):
            return True
    return False

def _extract_common_names_from_filenames(file_contents: List[Dict[str, Any]]) -> Set[str]:
    """Scan filenames for common-name tokens (first/last)."""
    names: Set[str] = set()
    for fi in file_contents:
        filename = (fi.get('file_name') or '')
        # split on underscores, spaces, and hyphens
        parts = re.split(r"[ _-]+", filename)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            detected = is_top_common_name(part)
            if detected:
                names.add(detected)
    return names


def _identify_authors_from_zip(project_id: int) -> Set[str]:
    """Open the uploaded zip, try to read commit authors."""
    authors: Set[str] = set()
    if project_id <= 0:
        return authors

    zip_data = get_zip_file(project_id)
    if not (zip_data and isinstance(zip_data, (bytes, bytearray))):
        return authors

    try:
        ic = identify_contributors(zip_bytes=zip_data)
        repo_path = ic.extract_repo()
        if repo_path is not None:
            commit_counts = ic.get_commit_counts()  # {author: count}
            authors = set(commit_counts.keys())
        ic.cleanup()
    except Exception:
        # If anything about the archive/repo fails, just return empty set
        authors = set()
    return authors

def _compute_collab_score(indicators: Dict[str, Any], authors: Set[str]) -> int:
    """Compute collaboration score from indicators + author set."""
    score = 0
    if indicators['git_files'] > 0:
        score += 50
    if indicators['team_structure']:
        score += 25
    if len(authors) > 1:
        score += 50
    return min(score, 100)