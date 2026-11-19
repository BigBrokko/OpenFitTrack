"""Keeps web/openapi.json (and so the generated TypeScript types) in step with the API."""

import json
from pathlib import Path

from api.schema import export_schema, schema_json

SNAPSHOT = Path(__file__).resolve().parent.parent / "web" / "openapi.json"
HOW_TO_FIX = "The API changed. Run `npm run gen:api` in web/ and commit the result."


def test_the_committed_openapi_snapshot_is_current():
    assert SNAPSHOT.is_file(), f"web/openapi.json is missing. {HOW_TO_FIX}"

    committed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert committed == export_schema(), HOW_TO_FIX


def test_the_schema_text_is_stable():
    assert schema_json() == schema_json()
    assert schema_json().endswith("}\n")


def test_the_schema_describes_the_login_and_data_endpoints():
    paths = export_schema()["paths"]

    for path in ("/api/login", "/api/logout", "/api/me", "/api/day", "/api/goals"):
        assert path in paths
