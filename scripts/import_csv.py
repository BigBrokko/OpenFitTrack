"""Import foods from any CSV file (values per 100 g) into the database.

Without --per-100g it only shows what would be imported. Importing the same file again
updates the foods of that source instead of adding duplicates.

Usage:
  uv run python scripts/import_csv.py foods.csv                 # preview
  uv run python scripts/import_csv.py foods.csv --per-100g      # import
  uv run python scripts/import_csv.py foods.csv --name Product --kcal Energie --per-100g

In Docker (put the file in ./data, which is mounted at /import):
  docker compose run --rm app python scripts/import_csv.py /import/foods.csv --per-100g
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402

from core.csv_import import (  # noqa: E402
    default_source,
    foods_from_table,
    read_csv_table,
    resolve_mapping,
)
from core.db import create_db, get_engine  # noqa: E402
from core.foods import upsert_foods  # noqa: E402

COLUMN_OPTIONS = {
    "name": "column with the food name",
    "kcal": "column with kcal per 100 g",
    "kj": "column with kJ per 100 g (used when kcal is empty)",
    "protein_g": "column with protein (g) per 100 g",
    "carbs_g": "column with carbohydrates (g) per 100 g",
    "fat_g": "column with fat (g) per 100 g",
    "source_id": "column with an id, so a renamed food is updated instead of duplicated",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import foods from a CSV file.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--source", help="name of this source (default: from the file name)")
    parser.add_argument(
        "--per-100g",
        action="store_true",
        help="confirm that all values in the file are per 100 g, and import",
    )
    for field, help_text in COLUMN_OPTIONS.items():
        parser.add_argument(
            f"--{field.replace('_', '-')}", dest=field, metavar="COLUMN", help=help_text
        )
    args = parser.parse_args()

    try:
        table = read_csv_table(args.csv_path.read_bytes())
        mapping = resolve_mapping(
            list(table.frame.columns), {field: getattr(args, field) for field in COLUMN_OPTIONS}
        )
        source = args.source or default_source(args.csv_path.name)
        parsed = foods_from_table(table.frame, mapping, source)
    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")

    print(f"{len(table.frame)} lines, delimiter {table.delimiter!r}, encoding {table.encoding}")
    print(f"Columns: {mapping}")
    print(f"Usable: {len(parsed.foods)}, skipped: {len(parsed.skipped)}")
    for skipped in parsed.skipped[:10]:
        print(f"  line {skipped.row}: {skipped.reason}")
    if len(parsed.skipped) > 10:
        print(f"  ... and {len(parsed.skipped) - 10} more")

    if not args.per_100g:
        print("\nNothing imported. Check the columns above; add --per-100g to import.")
        return
    if not parsed.foods:
        sys.exit("Nothing to import.")

    engine = get_engine()
    create_db(engine)
    with Session(engine) as session:
        result = upsert_foods(session, parsed.foods, source)
    print(f"Source '{source}': {result.added} added, {result.updated} updated.")


if __name__ == "__main__":
    main()
