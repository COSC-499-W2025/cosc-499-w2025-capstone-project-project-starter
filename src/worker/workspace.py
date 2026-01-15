from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class SnapshotFileRow:
    relative_path: str
    file_sha256: str
    stored_path: str
    size_bytes: int
    last_modified_ts: Optional[datetime]


def materialize_snapshot_to_dir(files: Iterable[SnapshotFileRow]) -> str:
    """
    Materialize the snapshot into a temp directory, preserving relative paths.
    Uses hardlinks where possible, falls back to copy2.
    Returns the temp directory path (caller owns cleanup).
    """
    root = tempfile.mkdtemp(prefix="artifactminer-snap-")
    rootp = Path(root)

    for f in files:
        dst = rootp / f.relative_path
        dst.parent.mkdir(parents=True, exist_ok=True)

        src = f.stored_path
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    return root
