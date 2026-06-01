from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def _sqlite_connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


@lru_cache
def get_engine() -> Engine:
    """Create a cached SQLAlchemy engine."""

    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./"):
        relative_db_path = Path(settings.database_url.removeprefix("sqlite:///./"))
        relative_db_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_sqlite_connect_args(settings.database_url),
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached SQLAlchemy session factory."""

    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def initialize_database() -> None:
    """Create the database schema if it does not already exist."""

    from .models import Base  # Imported lazily to avoid circular imports.

    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a transactional session."""

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
