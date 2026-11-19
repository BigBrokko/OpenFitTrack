from datetime import datetime

import pytest
from sqlmodel import select

from core.meal_log import delete_entry, log_food, save_entries, update_entry
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


def test_log_food_by_id(session):
    kwark = add_food(session, "Kwark magere")

    entry = log_food(session, kwark.id, 200, datetime(2026, 1, 5, 8, 30))

    assert (entry.id, entry.food_id, entry.amount_g) == (1, kwark.id, 200)


def test_log_food_with_an_unknown_food(session):
    with pytest.raises(LookupError):
        log_food(session, 999, 100, datetime(2026, 1, 5, 8, 30))


def test_update_entry_changes_amount_and_time_but_not_the_food(session):
    kwark = add_food(session, "Kwark magere")
    (entry,) = save_entries(session, [(kwark, 200)], datetime(2026, 1, 5, 8, 30))

    updated = update_entry(session, entry.id, 150, datetime(2026, 1, 5, 9, 15))

    assert (updated.amount_g, updated.logged_at) == (150, datetime(2026, 1, 5, 9, 15))
    assert updated.food_id == kwark.id


def test_update_entry_keeps_the_time_when_none_is_given(session):
    kwark = add_food(session, "Kwark magere")
    (entry,) = save_entries(session, [(kwark, 200)], datetime(2026, 1, 5, 8, 30))

    updated = update_entry(session, entry.id, 150)

    assert (updated.amount_g, updated.logged_at) == (150, datetime(2026, 1, 5, 8, 30))


@pytest.mark.parametrize("grams", [0, -5])
def test_update_entry_rejects_non_positive_amounts(session, grams):
    kwark = add_food(session, "Kwark magere")
    (entry,) = save_entries(session, [(kwark, 200)], datetime(2026, 1, 5, 8, 30))

    with pytest.raises(ValueError):
        update_entry(session, entry.id, grams, datetime(2026, 1, 5, 8, 30))

    assert session.get(FoodEntry, entry.id).amount_g == 200


def test_update_entry_with_an_unknown_id(session):
    with pytest.raises(LookupError):
        update_entry(session, 999, 100, datetime(2026, 1, 5, 8, 30))


def test_delete_entry_removes_only_that_row(session):
    kwark = add_food(session, "Kwark magere")
    first, second = save_entries(session, [(kwark, 200), (kwark, 100)], datetime(2026, 1, 5, 8, 0))

    delete_entry(session, first.id)

    assert [e.id for e in session.exec(select(FoodEntry)).all()] == [second.id]


def test_delete_entry_with_an_unknown_id(session):
    with pytest.raises(LookupError):
        delete_entry(session, 999)
