"""
SQLAlchemy engine + session management.

Defaults to a local SQLite file so the project runs out of the box with
zero external services. Point DATABASE_URL at Postgres for production,
e.g. postgresql+psycopg2://user:pass@localhost:5432/reposage
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Call once on startup (dev convenience; use Alembic in prod)."""
    from app.models import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)
