"""The OpenAPI description of the API, without starting a server or opening a database.

Used to generate the TypeScript types of the web app (see scripts/export_openapi.py) and by
a test that checks the committed snapshot is current.
"""

import json

from argon2 import PasswordHasher
from sqlmodel import create_engine

from api.auth import AuthSettings
from api.main import create_app


def export_schema() -> dict:
    # The schema does not contain any setting; these values only let the app be built.
    settings = AuthSettings(
        password_hash=PasswordHasher().hash("not-a-real-password"),
        session_secret="x" * 32,
    )
    return create_app(create_engine("sqlite://"), settings).openapi()


def schema_json() -> str:
    """Stable text form (sorted keys), so the committed file only changes with the API."""
    return json.dumps(export_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
