"""
example_retrieval.py
--------------------
Utility script that fetches the most recent stored insights and prints a summary
identical to the pipeline output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.insights.storage import ArtifactVideoHint, ProjectInsightsStore


def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def count_misc_files(payload: Dict[str, Any]) -> int:
    categorized = payload.get("categorized_contents", {})
    return sum(len(categorized.get(key, [])) for key in ("code", "documentation", "images"))


def describe_languages(categorized: Dict[str, Any]) -> List[Tuple[str, int]]:
    lang_map = categorized.get("code_by_language", {})
    sorted_items = sorted(lang_map.items(), key=lambda item: len(item[1]), reverse=True)
    return [(lang, len(files)) for lang, files in sorted_items]


def doc_summary(analysis: Dict[str, Any]) -> Tuple[int, int]:
    doc_data = analysis.get("documentation")
    if isinstance(doc_data, dict):
        totals = doc_data.get("totals", {})
        return totals.get("total_files", 0), totals.get("total_words", 0)
    return 0, 0


def image_summary(analysis: Dict[str, Any]) -> Tuple[int, float]:
    img_data = analysis.get("images")
    if isinstance(img_data, list):
        total_size = sum(item.get("file_stats", {}).get("size_mb", 0.0) for item in img_data)
        return len(img_data), total_size
    return 0, 0.0


def code_summary(analysis: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    code_data = analysis.get("code")
    if isinstance(code_data, dict):
        metrics = code_data.get("metrics", {})
        return (
            metrics.get("total_files", 0),
            metrics.get("total_lines", 0),
            metrics.get("languages", []),
        )
    return 0, 0, []


def video_summary(analysis: Dict[str, Any]) -> Tuple[int, float]:
    video_data = analysis.get("videos")
    if isinstance(video_data, dict):
        metrics = video_data.get("metrics", {})
        return metrics.get("total_videos", 0), metrics.get("total_duration", 0.0)
    return 0, 0.0


def print_presentation(payload: Dict[str, Any]) -> None:
    portfolio = payload.get("portfolio_item")
    resume = payload.get("resume_item")
    if not portfolio and not resume:
        return
    print("\n   Presentation:")
    if portfolio:
        print("      - Portfolio:")
        try:
            print(json.dumps(portfolio, indent=8))
        except Exception:
            print(f"        {portfolio}")
    if resume:
        bullets = resume.get("bullets", [])
        print("      - Resume bullets:")
        if bullets:
            for b in bullets:
                print(f"         • {b}")
        else:
            print("         (none)")


def print_global_sections(extras: Dict[str, Any]) -> None:
    """Pretty-print ranking and timeline from stored global insights."""
    if not extras:
        return

    ranking = extras.get("project_ranking") or extras.get("ranking_results") or {}
    timeline = extras.get("chronological_skills") or {}

    print("\n" + "=" * 70)
    print("🏆 PROJECT RANKING & SUMMARIES (stored)")
    print("=" * 70)
    if ranking:
        try:
            print(json.dumps(ranking, indent=2, sort_keys=True))
        except Exception:
            print(ranking)
    else:
        print("No project ranking data available")

    print("\n" + "=" * 70)
    print("📅 CHRONOLOGICAL SKILLS TIMELINE (stored)")
    print("=" * 70)
    if timeline:
        try:
            print(json.dumps(timeline, indent=2, sort_keys=True))
        except Exception:
            print(timeline)
    else:
        print("No chronological skills data available")


def print_project_summary(project_name: str, payload: Dict[str, Any]) -> None:
    print("\n" + "-" * 70)
    print(f"Project: {project_name}")
    print("-" * 70)

    is_git = payload.get("is_git_repo", False)
    print(f"   Git Repository: {'YES' if is_git else 'NO'}")

    categorized = payload.get("categorized_contents", {})
    print("\n   File Categorization:")
    code_files = len(categorized.get("code", []))
    doc_files = len(categorized.get("documentation", []))
    image_files = len(categorized.get("images", []))
    lang_counts = describe_languages(categorized)
    print(f"      - Code files: {code_files}")
    if lang_counts:
        print("        Languages detected:")
        for lang, count in lang_counts[:5]:
            print(f"          - {lang}: {count} files")
    print(f"      - Documentation files: {doc_files}")
    print(f"      - Image files: {image_files}")
    video_ext_count = len(
        [
            path
            for path in categorized.get("other", [])
            if Path(path).suffix.lower() in ArtifactVideoHint.EXTENSIONS
        ]
    )
    print(f"      - Video files: {video_ext_count}")

    analysis = payload.get("analysis_results", {})
    print("\n   Analysis Results:")
    doc_files_count, doc_words = doc_summary(analysis)
    print(f"      - Documentation: {doc_files_count} files, {doc_words} words")
    img_count, img_size = image_summary(analysis)
    print(f"      - Images: {img_count} files, {img_size:.2f} MB")
    code_count, code_lines, languages = code_summary(analysis)
    langs_display = ", ".join(languages) if languages else "N/A"
    print(f"      - Code: {code_count} files, {code_lines} lines")
    print(f"        Languages: {langs_display}")
    video_count, duration = video_summary(analysis)
    print(f"      - Videos: {video_count} files, {duration:.1f}s duration")
    print_presentation(payload)
    if payload.get("global_insights"):
        print("      - Global insights attached (see section below for full JSON)")


def print_detailed_project_output(project_name: str, payload: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    header = (
        "MISCELLANEOUS FILES (not in any project)"
        if project_name == "_misc_files"
        else f"PROJECT: {project_name}"
    )
    print(header)
    print("=" * 70)

    analysis = payload.get("analysis_results", {})

    print("\n" + "-" * 70)
    print("DOCUMENTATION ANALYSIS")
    print("-" * 70)
    doc_data = analysis.get("documentation")
    if doc_data is None:
        print("No documentation files to analyze")
    elif isinstance(doc_data, dict) and "error" in doc_data:
        print(f"Error: {doc_data['error']}")
    else:
        print(json.dumps(doc_data, indent=2))

    print("\n" + "-" * 70)
    print("IMAGE ANALYSIS")
    print("-" * 70)
    img_data = analysis.get("images")
    if img_data is None:
        print("No image files to analyze")
    elif isinstance(img_data, dict) and "error" in img_data:
        print(f"Error: {img_data['error']}")
    elif img_data:
        for idx, img in enumerate(img_data, 1):
            stats = img.get("file_stats", {})
            resolution = img.get("resolution", {})
            print(f"\n[Image {idx}] {img.get('file_name', 'unknown')}")
            print(f"  Resolution: {resolution.get('width', 0)}x{resolution.get('height', 0)}")
            print(f"  Size: {stats.get('size_mb', 0):.2f} MB")
            print(f"  Format: {img.get('format', {}).get('format', 'unknown')}")
            content = img.get("content_classification", {})
            print(f"  Type: {content.get('primary_type', 'unknown')}")
    else:
        print("No image files found")

    print("\n" + "-" * 70)
    print("CODE ANALYSIS")
    print("-" * 70)
    code_data = analysis.get("code")
    if code_data is None:
        print("No code files to analyze")
    elif isinstance(code_data, dict) and "error" in code_data:
        print(f"Error: {code_data['error']}")
    elif code_data:
        files = code_data.get("files", [])
        if files:
            print(f"Individual File Analysis ({len(files)} files):")
            print(json.dumps(files, indent=2))
        metrics = code_data.get("metrics", {})
        print("\n" + "-" * 70)
        print("Aggregate Metrics Summary:")
        print(json.dumps(metrics, indent=2))
    else:
        print("No code files found")

    print("\n" + "-" * 70)
    print("VIDEO ANALYSIS")
    print("-" * 70)
    video_data = analysis.get("videos")
    if video_data is None:
        print("No video files to analyze")
    elif isinstance(video_data, dict) and "error" in video_data:
        print(f"Error: {video_data['error']}")
    elif video_data:
        print(json.dumps(video_data, indent=2))
    else:
        print("No video files found")

    presentation = {
        "portfolio_item": payload.get("portfolio_item"),
        "resume_item": payload.get("resume_item"),
    }
    if presentation["portfolio_item"] or presentation["resume_item"]:
        print("\n" + "-" * 70)
        print("PRESENTATION ITEMS")
        print("-" * 70)
        print(json.dumps(presentation, indent=2))


def select_zip_hash(store: ProjectInsightsStore, provided: Optional[str]) -> Optional[str]:
    if provided:
        return provided
    recent = store.list_recent_zipfiles(limit=1)
    if not recent:
        return None
    return recent[0]["zip_hash"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve and display stored project insights.")
    parser.add_argument("--zip-hash", help="Zip hash to retrieve. Defaults to the most recent entry.")
    parser.add_argument("--db-path", help="Override DB path used for retrieval.")
    args = parser.parse_args()

    store = ProjectInsightsStore(db_path=args.db_path)
    zip_hash = select_zip_hash(store, args.zip_hash)
    if not zip_hash:
        print("No stored insights found. Run the pipeline first.")
        sys.exit(1)

    metadata = store.get_zip_metadata(zip_hash)
    if not metadata:
        print(f"No metadata found for zip hash {zip_hash}")
        sys.exit(1)

    project_names = store.list_projects_for_zip(zip_hash)
    if not project_names:
        print(f"No projects stored for zip hash {zip_hash}")
        sys.exit(1)

    payloads = {}
    for name in project_names:
        payload = store.load_project_insight(zip_hash, name)
        if payload:
            payloads[name] = payload
    global_insights = None
    for data in payloads.values():
        if isinstance(data, dict) and "global_insights" in data:
            global_insights = data.get("global_insights")
            break

    misc_payload = payloads.pop("_misc_files", None)

    print("\n" + "=" * 70)
    print("Retrieval From Database")
    print("=" * 70)

    print("\nZIP Summary:")
    print(f"   - Total files: {metadata.get('file_count', 0)}")
    print(f"   - Uncompressed size: {format_bytes(metadata.get('total_uncompressed_bytes', 0))}")
    print(f"   - Compressed size: {format_bytes(metadata.get('total_compressed_bytes', 0))}")

    print(f"\nProjects Found: {len(payloads)}")
    if misc_payload:
        loose_count = count_misc_files(misc_payload)
        print(f"Miscellaneous Files: Yes ({loose_count} loose files)")
    else:
        print("Miscellaneous Files: No")

    if global_insights is not None:
        print("\nGlobal Insights (stored at project level):")
        try:
            print(json.dumps(global_insights, indent=2, sort_keys=True))
        except Exception:
            print(global_insights)
        print_global_sections(global_insights)

    for project_name, data in payloads.items():
        print_project_summary(project_name, data)

    if misc_payload:
        print("\n" + "-" * 70)
        print("Miscellaneous Files (not in any project)")
        print("-" * 70)
        categorized = misc_payload.get("categorized_contents", {})
        print("\n   File Categorization:")
        print(f"      - Code files: {len(categorized.get('code', []))}")
        code_langs = describe_languages(categorized)
        if code_langs:
            print("        Languages detected:")
            for lang, count in code_langs[:5]:
                print(f"          - {lang}: {count} files")
        print(f"      - Documentation files: {len(categorized.get('documentation', []))}")
        print(f"      - Image files: {len(categorized.get('images', []))}")
        print(
            f"      - Video files: {len([p for p in categorized.get('other', []) if Path(p).suffix.lower() in ArtifactVideoHint.EXTENSIONS])}"
        )

        analysis = misc_payload.get("analysis_results", {})
        print("\n   Analysis Results:")
        doc_files_count, doc_words = doc_summary(analysis)
        print(f"      - Documentation: {doc_files_count} files, {doc_words} words")
        code_count, code_lines, _ = code_summary(analysis)
        print(f"      - Code: {code_count} files, {code_lines} lines")

    print("\nCleaning up temporary directory...\n")

    print("\n" + "=" * 70)
    print("DETAILED ANALYSIS RESULTS BY PROJECT")
    print("=" * 70)

    for project_name, data in payloads.items():
        print_detailed_project_output(project_name, data)

    if misc_payload:
        print_detailed_project_output("_misc_files", misc_payload)

    print("\n" + "=" * 70)
    print("Retrieval Complete - All results printed above")
    print("=" * 70)


if __name__ == "__main__":
    main()
