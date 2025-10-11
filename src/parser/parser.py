"""
parser.py
---------
Core module for recursively parsing project directories and classifying files
as either text or binary. This serves as the foundation for subsequent
processing tasks such as categorization, metrics extraction, and ML-based
analysis.

Dependencies:
- file_classification.py : provides the `is_binary_file` function
"""

import os
from parser.file_classification import is_binary_file


def parse_directory(directory):
    """
    Recursively parse the given directory to classify files as binary or text.

    Args:
        directory (str): The path to the directory to parse.

    Returns:
        dict: A dictionary summarizing the files found, including:
            - total_files (int): total number of files found
            - binary_files (list[str]): list of binary file paths
            - text_files (list[str]): list of text file paths

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    summary = {
        "total_files": 0,
        "binary_files": [],
        "text_files": []
    }

    # Walk through all folders and subfolders in the directory
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            summary["total_files"] += 1

            # Use the helper function to check if the file is binary
            if is_binary_file(path):
                summary["binary_files"].append(path)
            else:
                summary["text_files"].append(path)

    return summary


def summarize_results(summary):
    """
    Print a readable summary of the parsed results.
    Useful for quick testing or debugging.

    Args:
        summary (dict): The dictionary returned by parse_directory().
    """
    print(f"Total files scanned: {summary['total_files']}")
    print(f"Binary files: {len(summary['binary_files'])}")
    print(f"Text files: {len(summary['text_files'])}")
