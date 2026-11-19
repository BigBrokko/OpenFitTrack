from datetime import date, datetime

import pytest
from sqlmodel import select

from core.foods import add_manual_food, list_manual_foods, update_manual_food
from core.matching import search_foods
from core.models import Food, FoodEntry
from core.nutrition import day_totals


def test_creates_a_manual_food(session):
    food = add_manual_food(session, "Eigen granola", 450, 10, 60, 18)

    assert food.id is not None
    assert (food.source, food.source_id) == ("manual", None)
    assert (food.kcal, food.protein_g, food.carbs_g, food.fat_g) == (450, 10, 60, 18)


def test_strips_the_name(session):
    assert add_manual_food(session, "  Eigen granola  ", 450, 10, 60, 18).name == "Eigen granola"


def test_new_food_can_be_found_by_search(session):
    add_manual_food(session, "Eigen granola", 450, 10, 60, 18)

    assert search_foods(session, "granola")[0].food.name == "Eigen granola"


@pytest.mark.parametrize("name", ["", "   "])
def test_rejects_empty_name(session, name):
    with pytest.raises(ValueError):
        add_manual_food(session, name, 100, 1, 1, 1)


@pytest.mark.parametrize(
    "values",
    [(-1, 1, 1, 1), (100, -1, 1, 1), (100, 1, -1, 1), (100, 1, 1, -0.1)],
)
def test_rejects_negative_values(session, values):
    with pytest.raises(ValueError):
        add_manual_food(session, "Test", *values)


def test_rejects_macros_above_100g(session):
    with pytest.raises(ValueError):
        add_manual_food(session, "Onmogelijk", 500, 50, 40, 11)


def test_allows_macros_of_exactly_100g(session):
    add_manual_food(session, "Pure olie en suiker", 500, 0, 50, 50)


def test_rejects_duplicate_manual_name_ignoring_case(session):
    add_manual_food(session, "Eigen granola", 450, 10, 60, 18)

    with pytest.raises(ValueError):
        add_manual_food(session, "eigen GRANOLA", 400, 8, 55, 15)

    assert len(session.exec(select(Food)).all()) == 1


def test_same_name_as_a_non_manual_food_is_allowed(session):
    session.add(
        Food(name="Kwark", source="nevo", source_id="1", kcal=60, protein_g=8, carbs_g=4, fat_g=0)
    )
    session.commit()

    assert add_manual_food(session, "Kwark", 70, 9, 4, 1).source == "manual"


# --- Editing -----------------------------------------------------------------


def test_lists_only_manual_foods_sorted_by_name(session):
    add_manual_food(session, "zout", 0, 0, 0, 0)
    add_manual_food(session, "Appel", 52, 0.3, 14, 0.2)
    session.add(Food(name="Aardappel", source="nevo", kcal=1, protein_g=1, carbs_g=1, fat_g=0))
    session.commit()

    assert [f.name for f in list_manual_foods(session)] == ["Appel", "zout"]


def test_updates_a_manual_food(session):
    food = add_manual_food(session, "Eigen granola", 450, 10, 60, 18)

    updated = update_manual_food(session, food.id, "Eigen granola v2", 400, 12, 55, 15)

    assert updated.id == food.id
    assert (updated.name, updated.kcal, updated.protein_g) == ("Eigen granola v2", 400, 12)


def test_logged_entries_follow_an_edited_food(session):
    food = add_manual_food(session, "Eigen granola", 400, 10, 60, 10)
    session.add(FoodEntry(food_id=food.id, logged_at=datetime(2026, 1, 5, 8), amount_g=100))
    session.commit()

    update_manual_food(session, food.id, "Eigen granola", 500, 10, 60, 10)

    assert day_totals(session, date(2026, 1, 5)).kcal == 500


def test_keeping_the_same_name_when_editing_is_allowed(session):
    food = add_manual_food(session, "Eigen granola", 450, 10, 60, 18)

    assert update_manual_food(session, food.id, "eigen granola", 400, 10, 60, 18).kcal == 400


def test_renaming_to_another_manual_food_is_rejected(session):
    add_manual_food(session, "Appel", 52, 0.3, 14, 0.2)
    other = add_manual_food(session, "Peer", 57, 0.4, 15, 0.1)

    with pytest.raises(ValueError):
        update_manual_food(session, other.id, "appel", 57, 0.4, 15, 0.1)


def test_imported_foods_cannot_be_edited(session):
    food = Food(
        name="Kwark", source="nevo", source_id="1", kcal=60, protein_g=8, carbs_g=4, fat_g=0
    )
    session.add(food)
    session.commit()

    with pytest.raises(ValueError, match="manual"):
        update_manual_food(session, food.id, "Kwark", 70, 8, 4, 0)


def test_editing_a_missing_food_is_rejected(session):
    with pytest.raises(ValueError):
        update_manual_food(session, 999, "X", 1, 1, 1, 0)


def test_editing_validates_the_values(session):
    food = add_manual_food(session, "Appel", 52, 0.3, 14, 0.2)

    with pytest.raises(ValueError):
        update_manual_food(session, food.id, "Appel", 52, 50, 40, 20)

    assert session.get(Food, food.id).protein_g == 0.3  # unchanged
