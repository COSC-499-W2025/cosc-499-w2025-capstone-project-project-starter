import os
from src.db.base import Base 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return url

_engine = None
_SessionLocal = None

def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine

_engine = get_engine()

SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

def get_db():
    """
    FastAPI dependency: yields a database session and ensures it is closed.
    Usage: def handler(..., db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    if _SessionLocal is None:
        get_engine()
    return _SessionLocal()
