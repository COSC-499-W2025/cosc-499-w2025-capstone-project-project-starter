import argparse
import os
import zipfile
import shutil
import tempfile
import re
import subprocess
import urllib.request
from datetime import datetime
from collections import Counter


# -------------------------
#  Helpers
# -------------------------

def classify_file(filepath: str) -> str:
    filename = filepath.lower()

    if re.search(r"test_|_test\.|/tests?/", filename):
        return "test"
    if filename.endswith((".py", ".js", ".java", ".cpp", ".c", ".ts")):
        return "code"
    if filename.endswith((".md", ".txt", ".rst", ".pdf")):
        return "document"
    if filename.endswith((".drawio", ".png", ".jpg", ".jpeg", ".svg")):
        return "design"

    return "other"


def compute_project_duration(directory):
    timestamps = []
    for root, _, files in os.walk(directory):
        for f in files:
            try:
                timestamps.append(os.path.getmtime(os.path.join(root, f)))
            except:
                pass

    if not timestamps:
        return None

    start = datetime.fromtimestamp(min(timestamps))
    end = datetime.fromtimestamp(max(timestamps))

    return {
        "start": start,
        "end": end,
        "duration_days": (end - start).days,
    }


def compute_activity_frequencies(directory):
    counter = Counter()
    for root, _, files in os.walk(directory):
        for f in files:
            activity = classify_file(f)
            counter[activity] += 1
    return dict(counter)


# -------------------------
#  Input source handling
# -------------------------

def handle_zip(path):
    temp = tempfile.mkdtemp()
    with zipfile.ZipFile(path, "r") as z:
        z.extractall(temp)
    return temp


def handle_github(url):
    """
    Downloads a GitHub repo as a ZIP using ?c= trick.
    """
    temp = tempfile.mkdtemp()
    zip_path = os.path.join(temp, "repo.zip")

    if not url.endswith(".zip"):
        if url.endswith("/"):
            url = url[:-1]
        url = url + "/archive/refs/heads/main.zip"

    urllib.request.urlretrieve(url, zip_path)

    return handle_zip(zip_path)


def resolve_source(path):
    if path.startswith("http://") or path.startswith("https://"):
        return handle_github(path)

    if os.path.isfile(path) and path.endswith(".zip"):
        return handle_zip(path)

    if os.path.isdir(path):
        return path

    raise ValueError("Invalid input: must be a folder, a zip file, or a GitHub repo URL.")


# -------------------------
# Main extraction entry
# -------------------------

def extract_metrics(path):
    resolved = resolve_source(path)
    duration = compute_project_duration(resolved)
    activity = compute_activity_frequencies(resolved)

    return {
        "project_root": resolved,
        "project_duration": duration,
        "activity_frequencies": activity,
        "total_files": sum(activity.values()),
    }


# -------------------------
#  CLI
# -------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract contribution metrics from a project directory, zip file, or GitHub repo URL."
    )
    parser.add_argument("source", help="Path/URL to project directory, .zip, or GitHub repo")
    args = parser.parse_args()

    metrics = extract_metrics(args.source)

    print("\n=== Project Metrics ===")
    print("Total files:", metrics["total_files"])

    print("\n--- Activity breakdown ---")
    for k, v in metrics["activity_frequencies"].items():
        print(f"{k:10s}: {v}")

    print("\n--- Project Duration ---")
    if metrics["project_duration"]:
        d = metrics["project_duration"]
        print("Start:", d["start"])
        print("End:  ", d["end"])
        print("Days: ", d["duration_days"])
    else:
        print("No duration info available.")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
