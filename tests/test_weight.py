from datetime import date

import pytest
from sqlmodel import select

from core.models import WeightEntry
from core.weight import list_weights, log_weight, trend_change, weight_trend


def entries(*pairs):
    return [WeightEntry(date=d, weight_kg=w) for d, w in pairs]


# --- Logging -----------------------------------------------------------------


def test_logs_a_weight(session):
    entry = log_weight(session, date(2026, 1, 5), 80.5)

    assert entry.id is not None
    assert (entry.date, entry.weight_kg) == (date(2026, 1, 5), 80.5)


def test_same_day_replaces_the_measurement(session):
    first = log_weight(session, date(2026, 1, 5), 80.5)
    second = log_weight(session, date(2026, 1, 5), 79.9)

    assert second.id == first.id
    (only,) = session.exec(select(WeightEntry)).all()
    assert only.weight_kg == 79.9


@pytest.mark.parametrize("weight", [0, -5, 19.9, 400.1, 750])
def test_rejects_implausible_weights(session, weight):
    with pytest.raises(ValueError):
        log_weight(session, date(2026, 1, 5), weight)

    assert list_weights(session) == []


@pytest.mark.parametrize("weight", [20, 400])
def test_accepts_the_range_limits(session, weight):
    assert log_weight(session, date(2026, 1, 5), weight).weight_kg == weight


def test_list_is_sorted_oldest_first(session):
    log_weight(session, date(2026, 1, 9), 80)
    log_weight(session, date(2026, 1, 2), 81)

    assert [w.date.day for w in list_weights(session)] == [2, 9]


# --- Trend -------------------------------------------------------------------


def test_trend_of_nothing_is_empty():
    result = weight_trend([])

    assert result.empty
    assert list(result.columns) == ["date", "weight_kg", "trend_kg"]


def test_first_trend_value_equals_first_measurement():
    result = weight_trend(entries((date(2026, 1, 1), 80.0)))

    assert result["trend_kg"].tolist() == [80.0]


def test_constant_weight_gives_constant_trend():
    data = entries((date(2026, 1, 1), 80), (date(2026, 1, 3), 80), (date(2026, 1, 9), 80))

    assert weight_trend(data)["trend_kg"].tolist() == pytest.approx([80, 80, 80])


def test_one_halflife_gap_weighs_old_and_new_measurement_equally_weighted():
    # 7 days apart with a 7-day half-life: old weight counts half as much as the new one.
    data = entries((date(2026, 1, 1), 80), (date(2026, 1, 8), 70))

    assert weight_trend(data)["trend_kg"].iloc[1] == pytest.approx((70 + 0.5 * 80) / 1.5)


def test_longer_gap_moves_the_trend_closer_to_the_new_measurement():
    short = weight_trend(entries((date(2026, 1, 1), 80), (date(2026, 1, 2), 70)))
    long = weight_trend(entries((date(2026, 1, 1), 80), (date(2026, 2, 1), 70)))

    assert long["trend_kg"].iloc[1] < short["trend_kg"].iloc[1] < 80
    assert long["trend_kg"].iloc[1] == pytest.approx(70, abs=0.5)


def test_halflife_is_adjustable():
    data = entries((date(2026, 1, 1), 80), (date(2026, 1, 2), 70))

    slow = weight_trend(data, halflife_days=30)["trend_kg"].iloc[1]
    fast = weight_trend(data, halflife_days=1)["trend_kg"].iloc[1]

    assert fast < slow


def test_unsorted_input_is_sorted_by_date():
    result = weight_trend(entries((date(2026, 1, 8), 70), (date(2026, 1, 1), 80)))

    assert result["weight_kg"].tolist() == [80, 70]


# --- Change ------------------------------------------------------------------


def test_trend_change_over_a_week():
    data = entries(
        (date(2026, 1, 1), 80),
        (date(2026, 1, 8), 79),
        (date(2026, 1, 15), 78),
    )
    trend = weight_trend(data)

    expected = trend["trend_kg"].iloc[2] - trend["trend_kg"].iloc[1]
    assert trend_change(trend) == pytest.approx(expected)
    assert trend_change(trend) < 0


def test_trend_change_is_none_without_enough_history():
    assert trend_change(weight_trend([])) is None
    assert trend_change(weight_trend(entries((date(2026, 1, 1), 80)))) is None
    assert (
        trend_change(weight_trend(entries((date(2026, 1, 1), 80), (date(2026, 1, 5), 79)))) is None
    )
