"""The helper of scripts/dev.py that rewrites the .env file."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "dev_script", Path(__file__).resolve().parent.parent / "scripts" / "dev.py"
)
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def test_upsert_env_replaces_empty_lines_and_keeps_the_rest():
    old = "DATABASE_URL=sqlite:///x.db\nOFT_PASSWORD_HASH=\n# comment\nOFT_COOKIE_SECURE=true\n"

    new = dev.upsert_env(old, {"OFT_PASSWORD_HASH": "$argon2id$abc", "OFT_SESSION_SECRET": "s"})

    assert new.splitlines() == [
        "DATABASE_URL=sqlite:///x.db",
        "# comment",
        "OFT_COOKIE_SECURE=true",
        "OFT_PASSWORD_HASH='$argon2id$abc'",
        "OFT_SESSION_SECRET='s'",
    ]


def test_upsert_env_on_an_empty_file():
    assert dev.upsert_env("", {"A": "1"}) == "A='1'\n"


def test_a_changed_value_is_not_duplicated():
    once = dev.upsert_env("", {"OFT_SESSION_SECRET": "one"})

    twice = dev.upsert_env(once, {"OFT_SESSION_SECRET": "two"})

    assert twice == "OFT_SESSION_SECRET='two'\n"
