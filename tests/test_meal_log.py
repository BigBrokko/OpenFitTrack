from datetime import datetime

import pytest
from sqlmodel import select

from core.meal_log import save_entries
from core.models import Food, FoodEntry


def add_food(session, name) -> Food:
    food = Food(name=name, source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)
    session.add(food)
    session.commit()
    return food


def test_save_entries_stores_rows(session):
    kwark = add_food(session, "Kwark magere")
    banaan = add_food(session, "Banaan")
    when = datetime(2026, 1, 5, 8, 30)

    save_entries(session, [(kwark, 200), (banaan, 120)], when)

    rows = session.exec(select(FoodEntry).order_by(FoodEntry.id)).all()
    assert [(r.food_id, r.amount_g) for r in rows] == [(kwark.id, 200), (banaan.id, 120)]
    assert all(r.logged_at == when for r in rows)


@pytest.mark.parametrize("grams", [0, -5])
def test_save_entries_rejects_non_positive_amounts(session, grams):
    kwark = add_food(session, "Kwark magere")

    with pytest.raises(ValueError):
        save_entries(session, [(kwark, grams)], datetime(2026, 1, 5, 8, 30))

    assert session.exec(select(FoodEntry)).all() == []


def test_one_failing_amount_saves_nothing(session):
    kwark = add_food(session, "Kwark magere")
    banaan = add_food(session, "Banaan")

    with pytest.raises(ValueError):
        save_entries(session, [(kwark, 100), (banaan, 0)], datetime(2026, 1, 5, 8, 30))

    assert session.exec(select(FoodEntry)).all() == []
