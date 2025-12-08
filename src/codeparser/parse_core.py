import os
from collections import defaultdict
from datetime import datetime
import zipfile
from . import file_classification
from ml.universal import predict


def _infer_project(root_dir, path):
    rel_path = os.path.relpath(path, root_dir)
    parts = rel_path.split(os.sep)
    return parts[0] if len(parts) > 1 else "__root__"



def read_zip_metadata(zip_path):
    """
    Return a mapping from archive-relative path -> metadata dict.

    Keys match the paths inside the ZIP (e.g. 'proj1/test.rs').
    """
    meta = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            # Skip directories
            if info.is_dir():
                continue

            rel_path = os.path.normpath(info.filename)

            meta[rel_path] = {
                # store POSIX timestamp (float)
                "modified": datetime(*info.date_time).timestamp(),
                "file_size": info.file_size,
                "compressed_size": info.compress_size,
                "crc": info.CRC,
                "mode_raw": info.external_attr,
                "zipinfo": info,
            }

    return meta


def parse_directory(root_dir, threshold=0.5, zip_metadata=None):
    """
    If `zip_metadata` is provided, it should be a mapping from
    archive-relative path (e.g. 'proj1/test.rs') to metadata dict
    as returned by `read_zip_metadata`.
    """
    results = []
    text_files = file_classification.list_text_files(root_dir)

    for path in text_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        rel_path = os.path.normpath(os.path.relpath(path, root_dir))

        archive_mtime = None
        if zip_metadata is not None:
            meta = zip_metadata.get(rel_path)
            if meta is not None:
                archive_mtime = meta["modified"]

        preds = predict.classify_text(content, threshold=threshold)

        results.append(
            {
                "file": path,
                "project": _infer_project(root_dir, path),
                "last_modified": archive_mtime,  # from ZIP, not from filesystem
                "predictions": preds,
            }
        )

    return results

def summarize_results(results):
    """
    Aggregate predictions across all files and print a summary.

    Global summary:
        - Aggregates skills across all files as before.
        - Returns a list of dicts with keys:
            - "skill"
            - "count" (# files where skill appears)
            - "avg_prob"
            - "max_prob"
        sorted by max_prob descending.

    Project-level summary (printed only):
        - Aggregates skills per project (top-level folder).
        - Projects are sorted chronologically by their last modified timestamp
          (oldest to newest).
    """
    # -------------------------------
    # Global skill aggregation
    # -------------------------------
    skill_scores = defaultdict(list)

    for item in results:
        for skill, prob in item.get("predictions", []):
            skill_scores[skill].append(prob)

    summary = []
    for skill, probs in skill_scores.items():
        if not probs:
            continue
        count = len(probs)
        avg_prob = sum(probs) / count
        max_prob = max(probs)
        summary.append(
            {
                "skill": skill,
                "count": count,
                "avg_prob": avg_prob,
                "max_prob": max_prob,
            }
        )

    summary.sort(key=lambda x: x["max_prob"], reverse=True)

    print("=== Skill summary across all non-binary files ===")
    for entry in summary:
        print(
            f"{entry['skill']}: "
            f"files={entry['count']}, "
            f"avg_prob={entry['avg_prob']:.3f}, "
            f"max_prob={entry['max_prob']:.3f}"
        )

    # -------------------------------
    # Project-level aggregation
    # -------------------------------
    project_skill_scores = defaultdict(lambda: defaultdict(list))
    project_last_modified = defaultdict(lambda: None)

    for item in results:
        project = item.get("project", "__root__")
        mtime = item.get("last_modified")

        if mtime is None:
            # Fallback in case older callers did not populate last_modified
            try:
                mtime = os.path.getmtime(item["file"])
            except OSError:
                mtime = None

        # Track most recent modification per project
        if mtime is not None:
            current = project_last_modified.get(project)
            if current is None or mtime > current:
                project_last_modified[project] = mtime

        # Aggregate skills per project
        for skill, prob in item.get("predictions", []):
            project_skill_scores[project][skill].append(prob)

    project_summaries = []
    for project, skills in project_skill_scores.items():
        skills_summary = []
        for skill, probs in skills.items():
            if not probs:
                continue
            count = len(probs)
            avg_prob = sum(probs) / count
            max_prob = max(probs)
            skills_summary.append(
                {
                    "skill": skill,
                    "count": count,
                    "avg_prob": avg_prob,
                    "max_prob": max_prob,
                }
            )

        skills_summary.sort(key=lambda x: x["max_prob"], reverse=True)

        project_summaries.append(
            {
                "project": project,
                "last_modified": project_last_modified.get(project),
                "skills": skills_summary,
            }
        )

    # Sort projects chronologically by last modified (oldest → newest)
    project_summaries.sort(
        key=lambda x: (x["last_modified"] is None, x["last_modified"] or 0.0)
    )

    print("\n=== Project skill summary (chronological by last modified) ===")
    for entry in project_summaries:
        ts = entry["last_modified"]
        if ts is not None:
            ts_str = datetime.fromtimestamp(ts).isoformat(sep=" ", timespec="seconds")
        else:
            ts_str = "N/A"

        print(f"\nProject: {entry['project']} (last modified: {ts_str})")
        for skill_entry in entry["skills"]:
            print(
                f"  {skill_entry['skill']}: "
                f"files={skill_entry['count']}, "
                f"avg_prob={skill_entry['avg_prob']:.3f}, "
                f"max_prob={skill_entry['max_prob']:.3f}"
            )

    # Keep return type backward compatible: global skill list only.
    return summary