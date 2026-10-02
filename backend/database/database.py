"""
SQLAlchemy engine, session factory, and declarative base for StudySense.

Usage (FastAPI dependency)::

    from backend.database.database import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        ...
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config.settings import settings

# check_same_thread=False is required for SQLite when used with FastAPI's
# async request handling (multiple threads may share the same connection).
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base — all ORM models inherit from this."""
    pass


def get_db():
    """FastAPI dependency: opens a DB session and guarantees it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables registered on Base.

    Called once at application startup.  Safe to call multiple times —
    SQLAlchemy only creates tables that do not already exist.
    """
    # Importing models here ensures their classes are registered on Base
    # before create_all is called.
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
