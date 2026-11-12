"""Tool logic: reads from `core` and shapes the answers. No MCP imports here.

All numbers come from the user's own database and from plain Python in `core`.
Values are rounded to one decimal to keep the answers short.
"""

import datetime as dt

from sqlmodel import Session

from core.day_summary import Progress, compare_to_goal, day_entries
from core.db import get_current_goal
from core.goals import list_goals
from core.matching import search_foods as core_search_foods
from core.models import Goal
from core.nutrition import Nutrients
from core.stats import period_stats
from core.weight import list_weights, trend_change, weight_trend
from mcp_server.models import (
    DaySummary,
    DayTotals,
    FoodCandidate,
    FoodSearchResult,
    GoalInfo,
    GoalsInfo,
    LoggedEntry,
    NutrientValues,
    PeriodSummary,
    ProgressItem,
    WeightPoint,
    WeightTrend,
)


def _round(value: float) -> float:
    return round(value, 1)


def _values(nutrients: Nutrients) -> NutrientValues:
    return NutrientValues(
        kcal=_round(nutrients.kcal),
        protein_g=_round(nutrients.protein_g),
        carbs_g=_round(nutrients.carbs_g),
        fat_g=_round(nutrients.fat_g),
    )


def _goal(goal: Goal) -> GoalInfo:
    return GoalInfo(
        valid_from=goal.valid_from,
        kcal=goal.kcal,
        protein_g=goal.protein_g,
        carbs_g=goal.carbs_g,
        fat_g=goal.fat_g,
        target_weight_kg=goal.target_weight_kg,
    )


def _progress(progress: dict[str, Progress]) -> dict[str, ProgressItem]:
    return {
        key: ProgressItem(
            eaten=_round(p.eaten),
            goal=_round(p.goal),
            remaining=_round(p.remaining),
            percent=_round(p.percent),
        )
        for key, p in progress.items()
    }


def day_summary(session: Session, day: dt.date) -> DaySummary:
    entries = day_entries(session, day)
    totals = Nutrients.zero()
    for entry in entries:
        totals += entry.nutrients

    goal = get_current_goal(session, day)
    return DaySummary(
        date=day,
        totals=_values(totals),
        goal=_goal(goal) if goal else None,
        progress=_progress(compare_to_goal(totals, goal)) if goal else None,
        entries=[
            LoggedEntry(
                time=f"{e.logged_at:%H:%M}",
                food=e.food_name,
                amount_g=_round(e.amount_g),
                nutrients=_values(e.nutrients),
            )
            for e in entries
        ],
        note=None
        if entries
        else "Nothing is logged on this day. That does not mean nothing was eaten.",
    )


def period_summary(session: Session, start: dt.date, end: dt.date) -> PeriodSummary:
    stats = period_stats(session, start, end)
    average = stats.average_per_logged_day
    goal = get_current_goal(session, end)

    note = None
    if stats.days_logged < stats.days_in_period:
        note = (
            f"Food is logged on {stats.days_logged} of {stats.days_in_period} days. Averages use "
            "only those days; a day without entries usually means it was not logged."
        )
    return PeriodSummary(
        start_date=start,
        end_date=end,
        days_in_period=stats.days_in_period,
        days_logged=stats.days_logged,
        daily=[DayTotals(date=day, totals=_values(n)) for day, n in stats.daily],
        average_per_logged_day=_values(average) if average else None,
        goal_on_end_date=_goal(goal) if goal else None,
        average_vs_goal=_progress(compare_to_goal(average, goal)) if average and goal else None,
        note=note,
    )


def weight_summary(session: Session, days: int, today: dt.date) -> WeightTrend:
    weights = list_weights(session)
    trend = weight_trend(weights)  # the trend needs the full history, not just the window
    goal = get_current_goal(session, today)

    window_start = today - dt.timedelta(days=days)
    points = [
        WeightPoint(
            date=row.date.date(), weight_kg=_round(row.weight_kg), trend_kg=_round(row.trend_kg)
        )
        for row in trend.itertuples()
        if row.date.date() >= window_start
    ]
    change = trend_change(trend)
    return WeightTrend(
        points=points,
        measurements_total=len(weights),
        latest_weight_kg=_round(trend.iloc[-1].weight_kg) if len(trend) else None,
        latest_trend_kg=_round(trend.iloc[-1].trend_kg) if len(trend) else None,
        trend_change_7d_kg=_round(change) if change is not None else None,
        target_weight_kg=goal.target_weight_kg if goal else None,
    )


def goals_summary(session: Session, today: dt.date) -> GoalsInfo:
    current = get_current_goal(session, today)
    return GoalsInfo(
        current=_goal(current) if current else None,
        history=[_goal(g) for g in list_goals(session)],
    )


def food_search(session: Session, query: str, limit: int) -> FoodSearchResult:
    matches = core_search_foods(session, query, limit=limit)
    return FoodSearchResult(
        query=query,
        results=[
            FoodCandidate(
                name=m.food.name,
                source=m.food.source,
                kcal=_round(m.food.kcal),
                protein_g=_round(m.food.protein_g),
                carbs_g=_round(m.food.carbs_g),
                fat_g=_round(m.food.fat_g),
                score=_round(m.score),
            )
            for m in matches
        ],
    )
