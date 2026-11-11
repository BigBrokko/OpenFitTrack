from datetime import date, datetime

import pytest

from core.models import Food, FoodEntry
from core.nutrition import Nutrients, day_totals, entry_nutrients

DAY = date(2026, 1, 5)


def add_food(session, name="Kwark", kcal=60.0, protein=10.0, carbs=4.0, fat=0.2) -> Food:
    food = Food(name=name, source="manual", kcal=kcal, protein_g=protein, carbs_g=carbs, fat_g=fat)
    session.add(food)
    session.commit()
    return food


def add_entry(session, food, logged_at, amount_g):
    session.add(FoodEntry(food_id=food.id, logged_at=logged_at, amount_g=amount_g))
    session.commit()


def test_entry_nutrients_scales_per_100g():
    food = Food(name="Kwark", source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)

    result = entry_nutrients(food, 200)

    assert result.kcal == pytest.approx(120)
    assert result.protein_g == pytest.approx(20)
    assert result.carbs_g == pytest.approx(8)
    assert result.fat_g == pytest.approx(0.4)


def test_entry_nutrients_zero_grams_is_zero():
    food = Food(name="Kwark", source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)

    assert entry_nutrients(food, 0) == Nutrients.zero()


def test_entry_nutrients_rejects_negative_amount():
    food = Food(name="Kwark", source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)

    with pytest.raises(ValueError):
        entry_nutrients(food, -1)


def test_nutrients_add():
    total = Nutrients(100, 10, 20, 5) + Nutrients(50, 1, 2, 3)

    assert total == Nutrients(150, 11, 22, 8)


def test_day_totals_sums_entries_of_the_day(session):
    kwark = add_food(session)
    banaan = add_food(session, "Banaan", kcal=90, protein=1, carbs=20, fat=0.3)
    add_entry(session, kwark, datetime(2026, 1, 5, 8, 0), 200)
    add_entry(session, banaan, datetime(2026, 1, 5, 12, 30), 100)

    total = day_totals(session, DAY)

    assert total.kcal == pytest.approx(120 + 90)
    assert total.protein_g == pytest.approx(20 + 1)
    assert total.carbs_g == pytest.approx(8 + 20)
    assert total.fat_g == pytest.approx(0.4 + 0.3)


def test_day_totals_respects_day_boundaries(session):
    food = add_food(session, kcal=100)
    add_entry(session, food, datetime(2026, 1, 4, 23, 59), 100)  # previous day
    add_entry(session, food, datetime(2026, 1, 5, 0, 0), 100)  # first moment of the day
    add_entry(session, food, datetime(2026, 1, 5, 23, 59), 100)  # last minute of the day
    add_entry(session, food, datetime(2026, 1, 6, 0, 0), 100)  # next day

    assert day_totals(session, DAY).kcal == pytest.approx(200)


def test_day_totals_empty_day_is_zero(session):
    assert day_totals(session, DAY) == Nutrients.zero()
