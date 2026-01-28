#collaborative/identify_projects.py
from names_dataset import NameDataset
import re
import unicodedata
from typing import Dict, List, Set, Tuple, Any
from parsing.file_contents_manager import get_zip_file
from collaborative.identify_contributors import identify_contributors
from functools import lru_cache

# Lazy-loaded NameDataset instance
_name_dataset = None

def _get_name_dataset():
    """Lazy-load NameDataset only when needed."""
    global _name_dataset
    if _name_dataset is None:
        _name_dataset = NameDataset()
    return _name_dataset

RANK_THRESHOLD = 25  # "Top 100" cutoff

def _normalize_name(s: str) -> str:
    # NFKC handles width/compatibility; casefold() for case-insensitive match
    return unicodedata.normalize("NFKC", s).casefold().strip()

def _letters_only_unicode(s: str) -> str:
    # Keep all Unicode letters + space/'/’/-
    kept = []
    for ch in s:
        if ch.isalpha() or ch in (" ", "-", "'", "’"):
            kept.append(ch)
    return "".join(kept).strip()

@lru_cache(maxsize=10_000)
def _search_name_cached(key: str):
    # nd.search expects the original casing; use the original token later
    # but de-dupe work with cache on the normalized key
    # We'll pass the original key (title() is fine) to nd.search for better hit rates
    try:
        # Using title-cased form tends to align with dataset entries
        nd = _get_name_dataset()
        return nd.search(key.title())
    except Exception:
        return None

def _rank_below_threshold(search_block: dict, kind: str, threshold: int) -> bool:
    """
    search_block: full result from nd.search(...)
    kind: "first_name" or "last_name"
    Returns True if any rank value < threshold for that kind.
    """
    if not search_block or kind not in search_block:
        return False
    kinfo = search_block[kind] or {}
    ranks = kinfo.get("rank") or {}
    # ranks is a dict: {CountryName: rank_int}
    for _country, rank in ranks.items():
        try:
            if rank is not None and int(rank) < threshold:
                return True
        except (TypeError, ValueError):
            continue
    return False

def is_top_common_name(word: str, threshold: int = RANK_THRESHOLD):
    """
    Return title-cased `word` if it's top-ranked (< threshold) as a first or last name
    in ANY country according to nd.search(); else None.

    - Handles Unicode letters, accents, and multi-word names.
    - Uses caching for speed on repeated lookups.
    """
    token = _letters_only_unicode(word)
    if not token:
        return None

    key = _normalize_name(token)
    result = _search_name_cached(key)
    if not result:
        return None

    if (_rank_below_threshold(result, "first_name", threshold) or
        _rank_below_threshold(result, "last_name", threshold)):
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
    """Scan filenames and paths for common-name tokens (first/last)."""
    names: Set[str] = set()
    for fi in file_contents:
        # Check both filename and full path
        texts = [fi.get('file_name') or '', fi.get('file_path') or '']
        for text in texts:
            # Split on delimiters and CamelCase boundaries
            parts = re.split(r"[ _/\\-]+", text)
            for part in parts:
                # Also split CamelCase (e.g., "EvanPasenau" -> ["Evan", "Pasenau"])
                camel_parts = re.findall(r'[A-Z][a-z]+|[a-z]+', part)
                for p in (camel_parts if camel_parts else [part]):
                    p = p.strip()
                    if not p:
                        continue
                    detected = is_top_common_name(p)
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
    if indicators['has_common_names']:
        score += 40
    return min(score, 100)