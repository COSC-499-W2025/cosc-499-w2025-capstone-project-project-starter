"""
Evidence extractor for resume/portfolio projects.

Goal:
- Turn existing project metrics into short "evidence of success" bullets that
  can be shown on a resume/portfolio showcase.
- Pure logic (no DB, no network), easy to unit test.

Expected inputs (best-effort, everything optional):
- languages: {"languages": [...], "primary_language": "..."}
- frameworks: [...]
- time_analysis: {"duration_days": int, "intensity": str, "first_file": str, "last_file": str}
- collaboration_analysis: {"collaboration_level": str}
- code_analysis: may include {"code_quality_summary": {"average_quality_score": float}}
- project_structure: {"has_tests": bool, "has_docs": bool}
- file_statistics: {"total_lines_of_code": int, "total_files": int, ...}
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


def build_evidence(project_summary: Dict[str, Any]) -> List[str]:
    """
    Build evidence bullets for a single project.

    Args:
        project_summary: Dict containing project summary + optional metrics.

    Returns:
        List[str]: 1..N evidence bullets (short and resume-friendly).
    """
    evidence: List[str] = []

    # --- Pull data from common locations (best-effort) ---
    languages_block = _as_dict(project_summary.get("languages"))
    detected_langs = _as_list(
    languages_block.get("languages") or languages_block.get("detected_languages")
    )

    primary_lang = languages_block.get("primary_language", "Unknown")

    frameworks = _as_list(project_summary.get("frameworks"))
    if isinstance(frameworks, dict):
        frameworks = list(frameworks.keys())

    time_analysis = _as_dict(project_summary.get("time_analysis"))
    duration_days = _safe_int(time_analysis.get("duration_days"), default=0)
    intensity = (time_analysis.get("intensity") or "").strip()
    first_file = (time_analysis.get("first_file") or "").strip()
    last_file = (time_analysis.get("last_file") or "").strip()

    collab_analysis = _as_dict(project_summary.get("collaboration_analysis"))
    collab_level = (collab_analysis.get("collaboration_level") or "").strip()

    code_analysis = _as_dict(project_summary.get("code_analysis"))
    quality_score = _extract_quality_score(code_analysis)

    structure = _as_dict(project_summary.get("project_structure"))
    has_tests = bool(structure.get("has_tests", False))
    has_docs = bool(structure.get("has_docs", False))

    stats = _as_dict(project_summary.get("file_statistics"))
    # Some pipelines may store these under different keys; handle common variants.
    loc = _safe_int(
        stats.get("total_lines_of_code", stats.get("lines_of_code", stats.get("total_loc", 0))),
        default=0,
    )
    file_count = _safe_int(stats.get("total_files", stats.get("files", stats.get("file_count", 0))), default=0)

    # --- Evidence group 1: scale ---
    scale_line = _build_scale_evidence(loc=loc, files=file_count)
    if scale_line:
        evidence.append(scale_line)

    # --- Evidence group 2: timeline / effort ---
    timeline_line = _build_timeline_evidence(duration_days=duration_days, intensity=intensity, first_file=first_file, last_file=last_file)
    if timeline_line:
        evidence.append(timeline_line)

    # --- Evidence group 3: tech stack ---
    tech_line = _build_tech_evidence(detected_langs=detected_langs, primary_lang=primary_lang, frameworks=frameworks)
    if tech_line:
        evidence.append(tech_line)

    # --- Evidence group 4: quality signals ---
    quality_lines = _build_quality_evidence(has_tests=has_tests, has_docs=has_docs, quality_score=quality_score)
    evidence.extend(quality_lines)

    # --- Evidence group 5 (optional): collaboration ---
    collab_line = _build_collaboration_evidence(collab_level)
    if collab_line:
        evidence.append(collab_line)

    # Deduplicate while preserving order
    evidence = _dedupe_preserve_order([e.strip() for e in evidence if isinstance(e, str) and e.strip()])

    # Always return at least one line (fallback) so formatter has something to show.
    if not evidence:
        evidence = ["Delivered a complete project with measurable outputs and iterative improvements."]

    # Keep resume-friendly: cap to 5 bullets
    return evidence[:5]


# Helpers
def _safe_int(val: Any, default: int = 0) -> int:
    try:
        if val is None:
            return default
        if isinstance(val, bool):
            return default
        return int(val)
    except Exception:
        return default


def _format_big_number(n: int) -> str:
    # "2500" -> "2,500"
    try:
        return f"{n:,}"
    except Exception:
        return str(n)


def _extract_quality_score(code_analysis: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate a quality score from typical nested structures.
    """
    try:
        # Common in your ResumeManager test mocks:
        # code_analysis: { code_quality_summary: { average_quality_score: 85.5 } }
        q = (code_analysis.get("code_quality_summary") or {}).get("average_quality_score")
        if q is None:
            # Try a couple variants
            q = (code_analysis.get("quality") or {}).get("average_quality_score")
        if q is None:
            return None
        return float(q)
    except Exception:
        return None


def _build_scale_evidence(loc: int, files: int) -> str:
    if loc <= 0 and files <= 0:
        return ""

    parts = []
    if loc > 0:
        # Only add "+" if meaningful
        loc_part = _format_big_number(loc)
        if loc >= 500:
            parts.append(f"{loc_part}+ LOC")
        else:
            parts.append(f"{loc_part} LOC")

    if files > 0:
        files_part = _format_big_number(files)
        parts.append(f"{files_part} files")

    if parts:
        return f"Built and maintained a codebase spanning {', '.join(parts)}."
    return ""


def _build_timeline_evidence(duration_days: int, intensity: str, first_file: str, last_file: str) -> str:
    # Prefer precise duration if available; otherwise use intensity if meaningful.
    if duration_days > 0:
        if duration_days == 1:
            return "Completed a working iteration within 1 day."
        if duration_days < 14:
            return f"Delivered key iterations over {duration_days} days."
        return f"Developed over {duration_days} days, showing sustained progress."

    # If no duration, try using (first,last)
    if first_file and last_file and first_file != last_file:
        return f"Worked across the project timeline from {first_file} to {last_file}."

    if intensity and intensity.lower() != "unknown":
        return f"Demonstrated {intensity.lower()} development intensity through frequent updates."

    return ""


def _build_tech_evidence(detected_langs: Any, primary_lang: str, frameworks: Any) -> str:
    langs: List[str] = []
    if isinstance(detected_langs, list):
        langs = [str(x) for x in detected_langs if x]
    elif isinstance(detected_langs, str) and detected_langs.strip():
        langs = [detected_langs.strip()]

    fw: List[str] = []
    if isinstance(frameworks, list):
        fw = [str(x) for x in frameworks if x]
    elif isinstance(frameworks, str) and frameworks.strip():
        fw = [frameworks.strip()]

    # Keep it short: top 3 langs + top 3 frameworks
    langs = _dedupe_preserve_order(langs)[:3]
    fw = _dedupe_preserve_order(fw)[:3]

    if not langs and primary_lang and primary_lang != "Unknown":
        langs = [primary_lang]

    if langs and fw:
        return f"Tech stack: {', '.join(langs + fw)}."
    if langs:
        return f"Primary technologies: {', '.join(langs)}."
    if fw:
        return f"Built with: {', '.join(fw)}."
    return ""


def _build_quality_evidence(has_tests: bool, has_docs: bool, quality_score: Optional[float]) -> List[str]:
    lines: List[str] = []

    # Testing/doc signals
    if has_tests and has_docs:
        lines.append("Included automated tests and clear documentation to support maintainability.")
    elif has_tests:
        lines.append("Included automated tests to improve reliability and reduce regressions.")
    elif has_docs:
        lines.append("Produced technical documentation to support onboarding and long-term maintenance.")

    # Quality score signal (if present)
    if quality_score is not None:
        # Round nicely
        score = round(float(quality_score), 1)
        lines.append(f"Achieved an average code quality score of {score} based on static analysis signals.")

    return lines


def _build_collaboration_evidence(collab_level: str) -> str:
    if not collab_level:
        return ""
    lc = collab_level.lower()
    if lc == "unknown":
        return ""
    if "team" in lc or "collab" in lc:
        return "Collaborated with others using shared code ownership and coordinated changes."
    if "individual" in lc:
        return ""
    # fallback
    return f"Collaboration level: {collab_level}."


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def _as_dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _as_list(val: Any) -> List[Any]:
    # normalize common inputs into a list (best-effort)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, (tuple, set)):
        return list(val)
    if isinstance(val, dict):
        return list(val.keys())
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    # number/bool/other -> treat as empty
    return []
