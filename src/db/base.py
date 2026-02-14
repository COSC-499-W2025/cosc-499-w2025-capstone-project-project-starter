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
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    BigInteger,
    ForeignKey,
    func,
    text,
)


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


class FileBlob(Base):
    __tablename__ = "file_blobs"

    sha256 = Column(String(64), primary_key=True)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(128), nullable=True)
    stored_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PortfolioShowcase(Base):
    __tablename__ = "portfolio_showcases"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    project_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True
    )

    content_json = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    thumbnail_blob_sha256 = Column(
        String(64),
        ForeignKey("file_blobs.sha256", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Project(Base): 
    __tablename__ = "projects" 
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    portfolio_id = Column(PGUUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False) 
    name = Column(String, nullable=False) 
    project_type = Column(String, nullable=False) 
    collaboration_type = Column(String, nullable=False) 
    user_role = Column(String, nullable=True) 
    evidence_json = Column(JSONB, nullable=False, server_default="{}") 
    created_at = Column(DateTime(timezone=True), server_default=func.now())