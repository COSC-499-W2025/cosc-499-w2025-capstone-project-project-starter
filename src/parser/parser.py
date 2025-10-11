import os
from parser.file_classification import is_binary_file

def parse_directory(directory):
    """
    Recursively parse the given directory and return a structured summary:
    {
        "total_files": int,
        "binary_files": [file_paths],
        "text_files": [file_paths]
    }
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    summary = {
        "total_files": 0,
        "binary_files": [],
        "text_files": []
    }

    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            summary["total_files"] += 1
            if is_binary_file(path):
                summary["binary_files"].append(path)
            else:
                summary["text_files"].append(path)

    return summary


def summarize_results(summary):
    """
    Print a quick summary report to console (for debugging).
    """
    print(f"Total files: {summary['total_files']}")
    print(f"Binary files: {len(summary['binary_files'])}")
    print(f"Text files: {len(summary['text_files'])}")
