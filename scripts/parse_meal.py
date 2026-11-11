"""Smoke test: parse one meal description with your local Ollama model.

Needs a running Ollama server (`ollama serve`) and a pulled model (see OLLAMA_MODEL in
.env.example). Usage: uv run python scripts/parse_meal.py "200g kwark met een banaan"
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from core.parsing import ParseError, parse_meal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a meal description with Ollama.")
    parser.add_argument("text", help='e.g. "200g kwark met een banaan"')
    args = parser.parse_args()

    load_dotenv()
    try:
        meal = parse_meal(args.text)
    except ParseError as error:
        sys.exit(f"Parsing failed: {error}")

    if not meal.items:
        print("No food found in the text.")
    for item in meal.items:
        print(f"{item.quantity:g} {item.unit}  {item.name}")


if __name__ == "__main__":
    main()
