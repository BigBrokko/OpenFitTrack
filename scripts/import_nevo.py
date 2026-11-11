"""Import a NEVO CSV into the database.

Usage: uv run python scripts/import_nevo.py data/NEVO2025_v9.0/NEVO2025_v9.0.csv
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402

from core.db import create_db, get_engine  # noqa: E402
from core.nevo import import_foods, load_nevo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import NEVO foods into the database.")
    parser.add_argument("csv_path", type=Path, help="path to the main NEVO CSV file")
    args = parser.parse_args()

    foods, skipped = load_nevo(args.csv_path)
    engine = get_engine()
    create_db(engine)
    with Session(engine) as session:
        result = import_foods(session, foods)

    print(
        f"NEVO import done: {result.added} added, {result.updated} updated, "
        f"{skipped} skipped (not per 100 g or missing values)."
    )


if __name__ == "__main__":
    main()
