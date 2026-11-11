from datetime import datetime

import pytest
from sqlmodel import select

from core.meal_log import propose_entries, save_entries, unit_to_grams
from core.models import Food, FoodEntry
from core.parsing import ParsedItem, ParsedMeal


def add_food(session, name) -> Food:
    food = Food(name=name, source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)
    session.add(food)
    session.commit()
    return food


@pytest.mark.parametrize(
    ("quantity", "unit", "grams", "estimated"),
    [
        (200, "g", 200, False),
        (1.5, "kg", 1500, False),
        (250, "ml", 250, False),
        (1.5, "l", 1500, False),
        (2, "tbsp", 30, True),
        (1, "piece", 100, True),
        (0.5, "portion", 50, True),
    ],
)
def test_unit_to_grams(quantity, unit, grams, estimated):
    assert unit_to_grams(quantity, unit) == (grams, estimated)


def test_propose_entries_finds_candidates_and_grams(session):
    add_food(session, "Kwark magere")
    add_food(session, "Banaan")
    meal = ParsedMeal(
        items=[
            ParsedItem(name="kwark", quantity=200, unit="g"),
            ParsedItem(name="banaan", quantity=1, unit="piece"),
        ]
    )

    kwark, banaan = propose_entries(session, meal)

    assert kwark.candidates[0].food.name == "Kwark magere"
    assert (kwark.amount_g, kwark.estimated) == (200, False)
    assert banaan.candidates[0].food.name == "Banaan"
    assert (banaan.amount_g, banaan.estimated) == (100, True)


def test_propose_entries_keeps_items_without_candidates(session):
    add_food(session, "Kwark magere")
    meal = ParsedMeal(items=[ParsedItem(name="xyzqw", quantity=1, unit="piece")])

    (proposal,) = propose_entries(session, meal)

    assert proposal.candidates == []


def test_propose_entries_limits_candidates(session):
    for i in range(10):
        add_food(session, f"Kwark soort {i}")
    meal = ParsedMeal(items=[ParsedItem(name="kwark", quantity=100, unit="g")])

    (proposal,) = propose_entries(session, meal, candidates_per_item=3)

    assert len(proposal.candidates) == 3


def test_save_entries_stores_rows(session):
    kwark = add_food(session, "Kwark magere")
    banaan = add_food(session, "Banaan")
    when = datetime(2026, 1, 5, 8, 30)

    save_entries(session, [(kwark, 200), (banaan, 120)], when, raw_text="200g kwark en banaan")

    rows = session.exec(select(FoodEntry).order_by(FoodEntry.id)).all()
    assert [(r.food_id, r.amount_g) for r in rows] == [(kwark.id, 200), (banaan.id, 120)]
    assert all(r.logged_at == when for r in rows)
    assert rows[0].raw_text == "200g kwark en banaan"


@pytest.mark.parametrize("grams", [0, -5])
def test_save_entries_rejects_non_positive_amounts(session, grams):
    kwark = add_food(session, "Kwark magere")

    with pytest.raises(ValueError):
        save_entries(session, [(kwark, grams)], datetime(2026, 1, 5, 8, 30))

    assert session.exec(select(FoodEntry)).all() == []
