from datetime import date

import pytest

from core.db import get_current_goal
from core.goals import list_goals, set_goal


def test_saves_a_goal(session):
    goal = set_goal(session, date(2026, 1, 1), 2200, 160, 240, 65, target_weight_kg=75)

    assert goal.id is not None
    assert (goal.kcal, goal.target_weight_kg) == (2200, 75)


def test_target_weight_is_optional(session):
    assert set_goal(session, date(2026, 1, 1), 2200, 160, 240, 65).target_weight_kg is None


def test_new_date_keeps_old_goals(session):
    set_goal(session, date(2026, 1, 1), 2500, 150, 300, 70)
    set_goal(session, date(2026, 3, 1), 2200, 160, 240, 65)

    assert [g.kcal for g in list_goals(session)] == [2200, 2500]  # newest first
    assert get_current_goal(session, date(2026, 2, 1)).kcal == 2500
    assert get_current_goal(session, date(2026, 3, 1)).kcal == 2200


def test_same_date_replaces_the_goal(session):
    first = set_goal(session, date(2026, 1, 1), 2500, 150, 300, 70, target_weight_kg=80)
    second = set_goal(session, date(2026, 1, 1), 2300, 155, 270, 68)

    assert second.id == first.id
    (only,) = list_goals(session)
    assert (only.kcal, only.target_weight_kg) == (2300, None)


@pytest.mark.parametrize(
    "values",
    [
        {"kcal": 0},
        {"kcal": -100},
        {"protein_g": -1},
        {"carbs_g": -1},
        {"fat_g": -1},
        {"target_weight_kg": 0},
        {"target_weight_kg": -5},
    ],
)
def test_rejects_invalid_values(session, values):
    args = {"kcal": 2200, "protein_g": 160, "carbs_g": 240, "fat_g": 65} | values

    with pytest.raises(ValueError):
        set_goal(session, date(2026, 1, 1), **args)

    assert list_goals(session) == []
