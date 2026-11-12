import json
from pathlib import Path

import pytest

from core.parsing import ParsedItem
from evals.scoring import (
    EvalMeal,
    ExpectedItem,
    load_meals,
    score_meal,
    summarize,
)

MEALS_PATH = Path(__file__).resolve().parent.parent / "evals" / "meals.json"


def meal(*items: ExpectedItem) -> EvalMeal:
    return EvalMeal("m1", "dev", "tekst", tuple(items))


def expected(name, quantity, *units) -> ExpectedItem:
    return ExpectedItem(name, quantity, units)


def parsed(name, quantity, unit) -> ParsedItem:
    return ParsedItem(name=name, quantity=quantity, unit=unit)


# --- Scoring -----------------------------------------------------------------


def test_perfect_parse_passes():
    m = meal(expected("kwark", 200, "g"), expected("banaan", 1, "piece"))

    score = score_meal(m, [parsed("kwark", 200, "g"), parsed("banaan", 1, "piece")])

    assert score.passed
    assert (score.name_matches, score.full_matches, score.extra_items) == (2, 2, 0)


def test_name_is_matched_as_substring_ignoring_case():
    m = meal(expected("brood", 2, "slice"))

    assert score_meal(m, [parsed("Volkoren Brood", 2, "slice")]).passed


def test_any_listed_unit_counts():
    m = meal(expected("melk", 1, "portion", "cup"))

    assert score_meal(m, [parsed("melk", 1, "cup")]).passed
    assert score_meal(m, [parsed("melk", 1, "portion")]).passed
    assert not score_meal(m, [parsed("melk", 1, "ml")]).passed


def test_wrong_unit_is_counted_per_field():
    m = meal(expected("pindakaas", 2, "tbsp"))

    score = score_meal(m, [parsed("pindakaas", 2, "tsp")])

    assert not score.passed
    assert (score.name_matches, score.quantity_correct, score.unit_correct) == (1, 1, 0)
    assert score.full_matches == 0


def test_wrong_quantity_is_counted_per_field():
    m = meal(expected("avocado", 0.5, "piece"))

    score = score_meal(m, [parsed("avocado", 1, "piece")])

    assert (score.quantity_correct, score.unit_correct, score.full_matches) == (0, 1, 0)


def test_missing_item_fails_the_meal():
    m = meal(expected("kwark", 200, "g"), expected("banaan", 1, "piece"))

    score = score_meal(m, [parsed("kwark", 200, "g")])

    assert not score.passed
    assert (score.name_matches, score.full_matches) == (1, 1)


def test_extra_item_fails_the_meal():
    m = meal(expected("kwark", 200, "g"))

    score = score_meal(m, [parsed("kwark", 200, "g"), parsed("lepel", 1, "piece")])

    assert not score.passed
    assert score.extra_items == 1


def test_meal_without_food_passes_only_on_an_empty_parse():
    m = meal()

    assert score_meal(m, []).passed
    assert not score_meal(m, [parsed("kwark", 1, "piece")]).passed


def test_two_items_with_the_same_name_are_paired_with_the_best_candidates():
    m = meal(expected("ei", 3, "piece"), expected("ei", 1, "slice"))

    score = score_meal(m, [parsed("ei", 1, "slice"), parsed("ei", 3, "piece")])

    assert score.passed


def test_parse_error_counts_as_failure_with_nothing_matched():
    m = meal(expected("kwark", 200, "g"))

    score = score_meal(m, None, error="Cannot reach Ollama")

    assert not score.passed
    assert score.error == "Cannot reach Ollama"
    assert (score.name_matches, score.parsed) == (0, [])


def test_summary_aggregates_scores():
    good = score_meal(meal(expected("kwark", 200, "g")), [parsed("kwark", 200, "g")])
    bad_unit = score_meal(meal(expected("kaas", 3, "slice")), [parsed("kaas", 3, "piece")])
    failed = score_meal(meal(expected("ei", 2, "piece")), None, error="boom")

    summary = summarize([good, bad_unit, failed])

    assert (summary.meals, summary.passed, summary.errors) == (3, 1, 1)
    assert (summary.expected_items, summary.parsed_items, summary.full_matches) == (3, 2, 1)
    assert summary.meal_accuracy == pytest.approx(1 / 3)
    assert summary.recall == pytest.approx(1 / 3)
    assert summary.precision == pytest.approx(1 / 2)
    assert summary.name_accuracy == pytest.approx(2 / 3)
    assert summary.quantity_accuracy == 1.0
    assert summary.unit_accuracy == 0.5


def test_summary_of_nothing_has_no_ratios():
    summary = summarize([])

    assert summary.meal_accuracy is None
    assert summary.precision is None


# --- Loading and the real eval set --------------------------------------------


def write_meals(tmp_path, entries):
    path = tmp_path / "meals.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def entry(**overrides):
    base = {
        "id": "x1",
        "split": "dev",
        "text": "200g kwark",
        "items": [{"name": "Kwark", "quantity": 200, "units": ["g"]}],
    }
    return base | overrides


def test_load_meals_reads_entries(tmp_path):
    (loaded,) = load_meals(write_meals(tmp_path, [entry()]))

    assert loaded.id == "x1"
    assert loaded.items == (ExpectedItem("kwark", 200.0, ("g",)),)  # name is lowercased


@pytest.mark.parametrize(
    "bad",
    [
        entry(split="train"),
        entry(text="  "),
        entry(items=[{"name": "kwark", "quantity": 200, "units": ["bucket"]}]),
        entry(items=[{"name": "kwark", "quantity": 200, "units": []}]),
        entry(items=[{"name": "kwark", "quantity": 0, "units": ["g"]}]),
    ],
)
def test_load_meals_rejects_invalid_entries(tmp_path, bad):
    with pytest.raises(ValueError):
        load_meals(write_meals(tmp_path, [bad]))


def test_load_meals_rejects_duplicate_ids(tmp_path):
    with pytest.raises(ValueError):
        load_meals(write_meals(tmp_path, [entry(), entry()]))


def test_the_real_eval_set_is_valid_and_has_both_splits():
    meals = load_meals(MEALS_PATH)

    splits = {m.split for m in meals}
    assert splits == {"dev", "test"}
    assert sum(m.split == "dev" for m in meals) == 15
    assert sum(m.split == "test" for m in meals) >= 20
    assert any(not m.items for m in meals)  # at least one meal without food


def test_the_english_eval_set_is_valid_and_ids_do_not_clash_with_the_dutch_set():
    english = load_meals(MEALS_PATH.with_name("meals_en.json"))
    dutch_ids = {m.id for m in load_meals(MEALS_PATH)}

    assert len(english) >= 15
    assert any(not m.items for m in english)
    assert dutch_ids.isdisjoint(m.id for m in english)
