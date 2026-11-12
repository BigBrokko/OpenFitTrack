"""Scoring for the parsing eval. Plain Python, no Ollama needed.

A parsed item is paired with an expected item by name (the expected name must occur in
the parsed name, ignoring case). A pair is a full match when quantity and unit are also
right. A meal passes when every expected item fully matches and nothing extra was parsed.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from core.parsing import ParsedItem, Unit

VALID_UNITS = set(get_args(Unit))
VALID_SPLITS = {"dev", "test"}
QUANTITY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ExpectedItem:
    name: str
    quantity: float
    units: tuple[str, ...]  # every unit that counts as correct


@dataclass(frozen=True)
class EvalMeal:
    id: str
    split: str  # "dev": prompt was tuned on it, "test": never used for tuning
    text: str
    items: tuple[ExpectedItem, ...]


@dataclass
class MealScore:
    meal: EvalMeal
    parsed: list[ParsedItem]
    error: str | None
    name_matches: int
    quantity_correct: int
    unit_correct: int
    full_matches: int
    extra_items: int  # parsed items that were not paired with an expected item

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.full_matches == len(self.meal.items)
            and self.extra_items == 0
        )


@dataclass(frozen=True)
class Summary:
    meals: int
    passed: int
    errors: int
    expected_items: int
    parsed_items: int
    name_matches: int
    quantity_correct: int
    unit_correct: int
    full_matches: int

    @property
    def meal_accuracy(self) -> float | None:
        return _ratio(self.passed, self.meals)

    @property
    def recall(self) -> float | None:
        return _ratio(self.full_matches, self.expected_items)

    @property
    def precision(self) -> float | None:
        return _ratio(self.full_matches, self.parsed_items)

    @property
    def name_accuracy(self) -> float | None:
        return _ratio(self.name_matches, self.expected_items)

    @property
    def quantity_accuracy(self) -> float | None:
        """Among items whose name was found."""
        return _ratio(self.quantity_correct, self.name_matches)

    @property
    def unit_accuracy(self) -> float | None:
        """Among items whose name was found."""
        return _ratio(self.unit_correct, self.name_matches)


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def load_meals(path: str | Path) -> list[EvalMeal]:
    """Read and validate the eval set. Raises ValueError for a malformed file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    meals: list[EvalMeal] = []
    seen_ids: set[str] = set()
    for entry in raw:
        meal_id = entry["id"]
        if meal_id in seen_ids:
            raise ValueError(f"Duplicate meal id: {meal_id}")
        seen_ids.add(meal_id)
        if entry["split"] not in VALID_SPLITS:
            raise ValueError(f"{meal_id}: split must be one of {sorted(VALID_SPLITS)}")
        if not entry["text"].strip():
            raise ValueError(f"{meal_id}: text is empty")

        items = []
        for item in entry["items"]:
            units = tuple(item["units"])
            if not units or not set(units) <= VALID_UNITS:
                raise ValueError(f"{meal_id}: units must be a non-empty subset of {VALID_UNITS}")
            if item["quantity"] <= 0:
                raise ValueError(f"{meal_id}: quantity must be greater than 0")
            items.append(ExpectedItem(item["name"].lower(), float(item["quantity"]), units))
        meals.append(EvalMeal(meal_id, entry["split"], entry["text"], tuple(items)))
    return meals


def _quantity_ok(parsed: ParsedItem, expected: ExpectedItem) -> bool:
    return abs(parsed.quantity - expected.quantity) < QUANTITY_TOLERANCE


def _unit_ok(parsed: ParsedItem, expected: ExpectedItem) -> bool:
    return parsed.unit in expected.units


def score_meal(
    meal: EvalMeal, parsed: list[ParsedItem] | None, error: str | None = None
) -> MealScore:
    """Compare a parse with the expectation. Pass `error` when parsing itself failed."""
    parsed = [] if error is not None or parsed is None else list(parsed)
    unused = list(parsed)
    name_matches = quantity_correct = unit_correct = full_matches = 0

    for expected in meal.items:
        candidates = [p for p in unused if expected.name in p.name.lower()]
        if not candidates:
            continue
        # With several candidates (two "ei" items), take the one that is most correct.
        best = max(candidates, key=lambda p: _quantity_ok(p, expected) + _unit_ok(p, expected))
        unused.remove(best)
        quantity, unit = _quantity_ok(best, expected), _unit_ok(best, expected)
        name_matches += 1
        quantity_correct += quantity
        unit_correct += unit
        full_matches += quantity and unit

    return MealScore(
        meal=meal,
        parsed=parsed,
        error=error,
        name_matches=name_matches,
        quantity_correct=quantity_correct,
        unit_correct=unit_correct,
        full_matches=full_matches,
        extra_items=len(unused),
    )


def summarize(scores: list[MealScore]) -> Summary:
    return Summary(
        meals=len(scores),
        passed=sum(s.passed for s in scores),
        errors=sum(s.error is not None for s in scores),
        expected_items=sum(len(s.meal.items) for s in scores),
        parsed_items=sum(len(s.parsed) for s in scores),
        name_matches=sum(s.name_matches for s in scores),
        quantity_correct=sum(s.quantity_correct for s in scores),
        unit_correct=sum(s.unit_correct for s in scores),
        full_matches=sum(s.full_matches for s in scores),
    )
