import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from core.db import create_db


@pytest.fixture
def memory_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    create_db(engine)
    return engine


@pytest.fixture
def session(memory_engine):
    with Session(memory_engine) as session:
        yield session
