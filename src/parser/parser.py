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
        dict: A summary dictionary with:
            - total_files (int)
            - binary_files (list[str])
            - text_files (list[str])

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    binary_files = []
    text_files = []

    for file_path in _yield_all_files(directory):
        try:
            if is_binary_file(file_path):
                binary_files.append(file_path)
            else:
                text_files.append(file_path)
        except Exception as e:
            # Log or handle unreadable files if needed
            print(f"Warning: could not classify file '{file_path}': {e}")
            binary_files.append(file_path)  # Treat as binary by default

    return {
        "total_files": len(binary_files) + len(text_files),
        "binary_files": binary_files,
        "text_files": text_files
    }


def _yield_all_files(directory):
    """
    Generator that yields all file paths under the given directory recursively.

    Args:
        directory (str): Root directory to walk.

    Yields:
        str: Full path to each file found.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            yield os.path.join(root, file)


def summarize_results(summary):
    """
    Print a readable summary of the parsed results.

    Args:
        summary (dict): Dictionary returned by `parse_directory()`.
    """
    print("\n📊 Scan Summary")
    print("------------------")
    print(f"Total files scanned: {summary['total_files']}")
    print(f"Binary files       : {len(summary['binary_files'])}")
    print(f"Text files         : {len(summary['text_files'])}")
