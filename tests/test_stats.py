from datetime import date, datetime

import pytest

from core.models import Food, FoodEntry
from core.stats import MAX_PERIOD_DAYS, period_stats


@pytest.fixture
def kwark(session):
    food = Food(name="Kwark", source="manual", kcal=100, protein_g=10, carbs_g=4, fat_g=1)
    session.add(food)
    session.commit()
    return food


def log(session, food, when, grams):
    session.add(FoodEntry(food_id=food.id, logged_at=when, amount_g=grams))
    session.commit()


def test_sums_entries_per_day_oldest_first(session, kwark):
    log(session, kwark, datetime(2026, 1, 6, 12), 100)
    log(session, kwark, datetime(2026, 1, 5, 8), 200)
    log(session, kwark, datetime(2026, 1, 5, 19), 100)

    stats = period_stats(session, date(2026, 1, 5), date(2026, 1, 7))

    assert [(d, n.kcal) for d, n in stats.daily] == [
        (date(2026, 1, 5), 300),
        (date(2026, 1, 6), 100),
    ]
    assert stats.days_in_period == 3
    assert stats.days_logged == 2


def test_average_ignores_days_without_entries(session, kwark):
    log(session, kwark, datetime(2026, 1, 5, 8), 300)  # 300 kcal
    log(session, kwark, datetime(2026, 1, 7, 8), 100)  # 100 kcal; Jan 6 is not logged

    average = period_stats(session, date(2026, 1, 5), date(2026, 1, 7)).average_per_logged_day

    assert average.kcal == pytest.approx(200)  # not (300 + 0 + 100) / 3
    assert average.protein_g == pytest.approx(20)


def test_period_includes_both_end_days_and_excludes_others(session, kwark):
    log(session, kwark, datetime(2026, 1, 4, 23, 59), 100)  # before
    log(session, kwark, datetime(2026, 1, 5, 0, 0), 100)  # first moment of start day
    log(session, kwark, datetime(2026, 1, 7, 23, 59), 100)  # last minute of end day
    log(session, kwark, datetime(2026, 1, 8, 0, 0), 100)  # after

    stats = period_stats(session, date(2026, 1, 5), date(2026, 1, 7))

    assert [d.day for d, _ in stats.daily] == [5, 7]


def test_empty_period_has_no_average(session):
    stats = period_stats(session, date(2026, 1, 5), date(2026, 1, 7))

    assert stats.daily == []
    assert stats.days_logged == 0
    assert stats.average_per_logged_day is None


def test_single_day_period(session, kwark):
    log(session, kwark, datetime(2026, 1, 5, 8), 100)

    stats = period_stats(session, date(2026, 1, 5), date(2026, 1, 5))

    assert stats.days_in_period == 1


def test_rejects_an_end_before_the_start(session):
    with pytest.raises(ValueError):
        period_stats(session, date(2026, 1, 7), date(2026, 1, 5))


def test_rejects_a_period_longer_than_the_maximum(session):
    with pytest.raises(ValueError, match=str(MAX_PERIOD_DAYS)):
        period_stats(session, date(2025, 1, 1), date(2026, 1, 5))


def test_accepts_a_period_of_exactly_the_maximum(session):
    start = date(2025, 1, 1)
    end = date.fromordinal(start.toordinal() + MAX_PERIOD_DAYS - 1)

    assert period_stats(session, start, end).days_in_period == MAX_PERIOD_DAYS
