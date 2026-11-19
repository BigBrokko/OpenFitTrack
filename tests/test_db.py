import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from core.db import create_db, get_engine, get_readonly_engine


@pytest.fixture
def db_file(tmp_path):
    path = tmp_path / "my data" / "tracker.db"  # a space in the path on purpose
    path.parent.mkdir()
    engine = get_engine(f"sqlite:///{path.as_posix()}")
    create_db(engine)
    with engine.begin() as conn:
        conn.execute(text("insert into weight_entries (date, weight_kg) values ('2026-01-05', 80)"))
    engine.dispose()
    return path


def test_readonly_engine_can_read(db_file):
    engine = get_readonly_engine(f"sqlite:///{db_file.as_posix()}")

    with engine.connect() as conn:
        assert conn.execute(text("select weight_kg from weight_entries")).scalar() == 80


def test_readonly_engine_cannot_write(db_file):
    engine = get_readonly_engine(f"sqlite:///{db_file.as_posix()}")

    with engine.connect() as conn, pytest.raises(OperationalError, match="readonly"):
        conn.execute(text("delete from weight_entries"))
        conn.commit()

    with engine.connect() as conn:  # nothing was deleted
        assert conn.execute(text("select count(*) from weight_entries")).scalar() == 1


def test_readonly_engine_reads_the_url_from_the_environment(db_file, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

    with get_readonly_engine().connect() as conn:
        assert conn.execute(text("select count(*) from weight_entries")).scalar() == 1


def test_missing_file_fails_and_creates_nothing(tmp_path):
    missing = tmp_path / "nope.db"

    with pytest.raises(FileNotFoundError, match="DATABASE_URL"):
        get_readonly_engine(f"sqlite:///{missing.as_posix()}")

    assert not missing.exists()


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:", "postgresql://u:p@host/db"])
def test_only_sqlite_files_are_accepted(url):
    with pytest.raises(ValueError):
        get_readonly_engine(url)
