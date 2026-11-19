"""Database engine helpers."""

import os
from datetime import date
from pathlib import Path
from urllib.parse import quote

from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, SQLModel, create_engine, select

from core.models import Goal

DEFAULT_DATABASE_URL = "sqlite:///openfittrack.db"


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def get_readonly_engine(url: str | None = None) -> Engine:
    """Engine for an existing SQLite file that cannot write: SQLite itself rejects writes.

    Raises ValueError when the URL is not a SQLite file, and FileNotFoundError when the
    file does not exist (a normal engine would silently create an empty database).
    """
    parsed = make_url(url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    if (
        parsed.get_backend_name() != "sqlite"
        or not parsed.database
        or parsed.database == ":memory:"
    ):
        raise ValueError("A read-only engine needs a SQLite database file.")
    path = Path(parsed.database).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {path}. "
            "Set DATABASE_URL to the absolute path of your database."
        )
    return create_engine(f"sqlite:///file:{quote(path.as_posix(), safe='/:')}?mode=ro&uri=true")


def create_db(engine: Engine) -> None:
    # Importing core.models (above, via Goal) registers all tables on the metadata.
    SQLModel.metadata.create_all(engine)


def get_current_goal(session: Session, on: date) -> Goal | None:
    """Return the goal with the latest `valid_from` on or before the given date."""
    statement = select(Goal).where(Goal.valid_from <= on).order_by(Goal.valid_from.desc()).limit(1)
    return session.exec(statement).first()
