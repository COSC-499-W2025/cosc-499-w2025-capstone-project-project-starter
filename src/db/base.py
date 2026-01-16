from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.engine import Engine

class Base(DeclarativeBase):
    pass

#defining this twice is kinda stupid but so is python
@dataclass(frozen=True)
class SnapshotFileRow:
    relative_path: str
    file_sha256: str
    stored_path: str
    size_bytes: int
    last_modified_ts: Optional[datetime]


def fetch_snapshot_files(engine: Engine, snapshot_id: str) -> List[SnapshotFileRow]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT sf.relative_path, sf.file_sha256, fb.stored_path, sf.size_bytes, sf.last_modified_ts
                FROM snapshot_files sf
                JOIN file_blobs fb ON fb.sha256 = sf.file_sha256
                WHERE sf.snapshot_id = :sid
                ORDER BY sf.relative_path ASC
                """
            ),
            {"sid": snapshot_id},
        ).mappings().all()

    return [
        SnapshotFileRow(
            relative_path=r["relative_path"],
            file_sha256=r["file_sha256"],
            stored_path=r["stored_path"],
            size_bytes=int(r["size_bytes"]),
            last_modified_ts=r["last_modified_ts"],
        )
        for r in rows
    ]
