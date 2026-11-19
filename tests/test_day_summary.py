from datetime import date, datetime

import pytest

from core.day_summary import compare_to_goal, day_entries
from core.models import Food, FoodEntry, Goal
from core.nutrition import Nutrients

DAY = date(2026, 1, 5)


def add_entry(session, food, logged_at, amount_g):
    session.add(FoodEntry(food_id=food.id, logged_at=logged_at, amount_g=amount_g))
    session.commit()


@pytest.fixture
def kwark(session):
    food = Food(name="Kwark", source="manual", kcal=60, protein_g=10, carbs_g=4, fat_g=0.2)
    session.add(food)
    session.commit()
    return food


def test_entries_are_sorted_by_time_with_nutrients(session, kwark):
    add_entry(session, kwark, datetime(2026, 1, 5, 12, 0), 100)
    add_entry(session, kwark, datetime(2026, 1, 5, 8, 0), 200)

    first, second = day_entries(session, DAY)

    assert (first.logged_at.hour, first.amount_g, first.food_name) == (8, 200, "Kwark")
    assert first.nutrients.kcal == pytest.approx(120)
    assert second.nutrients.kcal == pytest.approx(60)


def test_entries_only_include_the_day(session, kwark):
    add_entry(session, kwark, datetime(2026, 1, 4, 23, 59), 100)
    add_entry(session, kwark, datetime(2026, 1, 5, 0, 0), 100)
    add_entry(session, kwark, datetime(2026, 1, 6, 0, 0), 100)

    assert len(day_entries(session, DAY)) == 1


def test_empty_day_has_no_entries(session):
    assert day_entries(session, DAY) == []


def make_goal():
    return Goal(valid_from=DAY, kcal=2000, protein_g=100, carbs_g=250, fat_g=60)


def test_compare_under_goal():
    result = compare_to_goal(Nutrients(500, 25, 50, 15), make_goal())

    kcal = result["kcal"]
    assert (kcal.eaten, kcal.goal, kcal.remaining, kcal.percent) == (500, 2000, 1500, 25)
    assert result["protein_g"].percent == 25
    assert result["carbs_g"].remaining == 200
    assert result["fat_g"].remaining == 45


def test_compare_over_goal_has_negative_remaining_and_percent_above_100():
    result = compare_to_goal(Nutrients(2400, 0, 0, 0), make_goal())

    assert result["kcal"].remaining == -400
    assert result["kcal"].percent == 120


def test_compare_with_zero_goal_does_not_divide_by_zero():
    goal = Goal(valid_from=DAY, kcal=2000, protein_g=0, carbs_g=250, fat_g=60)

    assert compare_to_goal(Nutrients(0, 20, 0, 0), goal)["protein_g"].percent == 0
