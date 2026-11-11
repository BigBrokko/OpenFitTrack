"""Database engine helpers."""

import os
from datetime import date

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from core.models import Goal

DEFAULT_DATABASE_URL = "sqlite:///openfittrack.db"


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def create_db(engine: Engine) -> None:
    # Importing core.models (above, via Goal) registers all tables on the metadata.
    SQLModel.metadata.create_all(engine)


def get_current_goal(session: Session, on: date) -> Goal | None:
    """Return the goal with the latest `valid_from` on or before the given date."""
    statement = select(Goal).where(Goal.valid_from <= on).order_by(Goal.valid_from.desc()).limit(1)
    return session.exec(statement).first()
