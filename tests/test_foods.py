import pytest
from sqlmodel import select

from core.foods import add_manual_food
from core.matching import search_foods
from core.models import Food


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
