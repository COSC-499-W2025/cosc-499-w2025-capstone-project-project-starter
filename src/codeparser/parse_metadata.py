# codeparser/metadata_parser.py

import os
import mimetypes
from datetime import datetime

def extract_metadata(file_path: str) -> dict:
    """Extract basic metadata from a file for the capstone project."""

    # Absolute path
    abs_path = os.path.abspath(file_path)

    # File name
    file_name = os.path.basename(file_path)

    # File extension
    _, ext = os.path.splitext(file_name)

    # File size in bytes
    file_size = os.path.getsize(file_path)

    # Last modified timestamp
    last_modified_ts = os.path.getmtime(file_path)
    last_modified = datetime.fromtimestamp(last_modified_ts).isoformat()
    
    data = {
        "file_name": file_name,
        "file_path": abs_path,
        "file_size": file_size,
        "file_extension": ext,
        "last_modified": last_modified,
    }

    print("DEBUG METADATA:", data)   # 👈 Debug print

    return data

def extract_metadata_directory(directory_path: str) -> list[dict]:
    """
    Extract metadata for all files in a directory (non-recursive).
    Returns a list of metadata dictionaries.
    """
    metadata_list = []

    for entry in os.scandir(directory_path):
        metadata = extract_metadata(entry.path)
        metadata_list.append(metadata)

    return metadata_list