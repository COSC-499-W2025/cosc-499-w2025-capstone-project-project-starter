"""Repository for project snapshots."""

from src.models.orm.project_snapshot import ProjectSnapshot
from src.repositories.base import BaseRepository


class SnapshotRepository(BaseRepository[ProjectSnapshot]):
    """Repository for project snapshot CRUD operations."""

    def __init__(self, db):
        super().__init__(ProjectSnapshot, db)
