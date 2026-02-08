"""
Data models for zip parsing functionality.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ZipEntry:
    """Represents a single file entry within a zip archive."""
    abs_path: str
    rel_path: str
    size: int
    compressed_size: int
    is_compressed: bool
    sha256: str
    depth: int
    ext: str
    is_text_guess: bool


@dataclass
class ZipIndex:
    """Represents the complete index of a parsed zip archive."""
    root_name: str
    file_count: int
    total_uncompressed_bytes: int
    total_compressed_bytes: int
    files: List[ZipEntry]