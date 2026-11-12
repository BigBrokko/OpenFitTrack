"""Run the parsing eval against local Ollama models and print a report.

Needs a running Ollama server and the models pulled. Examples:
  uv run python evals/run_evals.py
  uv run python evals/run_evals.py --model gemma3:12b --model qwen3:8b
  uv run python evals/run_evals.py --split test
  uv run python evals/run_evals.py --meals evals/meals_en.json
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ollama  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from core.parsing import DEFAULT_MODEL, ParseError, parse_meal  # noqa: E402
from evals.scoring import MealScore, Summary, load_meals, score_meal, summarize  # noqa: E402

MEALS_PATH = Path(__file__).resolve().parent / "meals.json"


def percent(value: float | None) -> str:
    return "  -  " if value is None else f"{value * 100:4.0f}%"


def format_expected(score: MealScore) -> str:
    items = [f"{i.quantity:g} {'/'.join(i.units)} {i.name}" for i in score.meal.items]
    return ", ".join(items) or "(no food)"


def format_parsed(score: MealScore) -> str:
    if score.error:
        return f"ERROR: {score.error}"
    return ", ".join(f"{i.quantity:g} {i.unit} {i.name}" for i in score.parsed) or "(no food)"


def print_summary_row(label: str, summary: Summary) -> None:
    print(
        f"{label:<6} {summary.meals:>5} {summary.passed:>6} "
        f"{percent(summary.meal_accuracy)}  {percent(summary.recall)} {percent(summary.precision)}"
        f"  {percent(summary.name_accuracy)} {percent(summary.quantity_accuracy)} "
        f"{percent(summary.unit_accuracy)}"
    )


def run_model(client: ollama.Client, model: str, meals: list) -> list[MealScore] | None:
    """Score every meal with one model. Returns None if the model cannot be used at all."""
    try:
        parse_meal("kwark", client=client, model=model)  # warm-up: loads the model into the GPU
    except ParseError as error:
        print(f"\n== {model}: skipped ({error})")
        return None

    scores = []
    start = time.perf_counter()
    for meal in meals:
        try:
            parsed = parse_meal(meal.text, client=client, model=model).items
            scores.append(score_meal(meal, parsed))
        except ParseError as error:
            scores.append(score_meal(meal, None, error=str(error)))
    seconds = (time.perf_counter() - start) / len(meals)

    print(f"\n== {model}  ({seconds:.2f} s per sentence)")
    print(
        f"{'set':<6} {'meals':>5} {'passed':>6} {'acc':>5}  {'recall':>5} {'prec':>5}"
        f"  {'name':>5} {'qty':>5} {'unit':>5}"
    )
    for label in ("dev", "test"):
        subset = [s for s in scores if s.meal.split == label]
        if subset:
            print_summary_row(label, summarize(subset))
    print_summary_row("all", summarize(scores))

    failures = [s for s in scores if not s.passed]
    if failures:
        print("\nFailed meals:")
        for score in failures:
            print(f"  [{score.meal.id}] {score.meal.text!r}")
            print(f"      expected: {format_expected(score)}")
            print(f"      got:      {format_parsed(score)}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate meal parsing with Ollama models.")
    parser.add_argument(
        "--model", action="append", help="model to test; repeat to compare (default: OLLAMA_MODEL)"
    )
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument(
        "--meals",
        type=Path,
        default=MEALS_PATH,
        help="eval set to use (default: evals/meals.json; also: evals/meals_en.json)",
    )
    args = parser.parse_args()

    load_dotenv()
    models = args.model or [os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)]
    meals = [m for m in load_meals(args.meals) if args.split in ("all", m.split)]

    print(f"{len(meals)} meals ({args.split}). acc = meals fully correct; recall/prec = items;")
    print("name/qty/unit = accuracy per field among items whose name was found.")
    client = ollama.Client()
    results = [run_model(client, model, meals) for model in models]
    if all(r is None for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
