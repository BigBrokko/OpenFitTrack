import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from core.db import create_db


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    create_db(engine)
    with Session(engine) as session:
        yield session
