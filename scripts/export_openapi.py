"""Write the API's OpenAPI description to web/openapi.json.

The web app generates its TypeScript types from that file: run `npm run gen:api` in web/,
which calls this script and then the type generator. Run it after every API change.

Usage: uv run python scripts/export_openapi.py
"""

import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.schema import schema_json  # noqa: E402

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "openapi.json"


def main() -> None:
    OUTPUT.write_text(schema_json(), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
