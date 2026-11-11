"""What was eaten on a day, and how it compares to the goal that applied then."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from core.models import Food, FoodEntry, Goal
from core.nutrition import Nutrients, entry_nutrients


@dataclass(frozen=True)
class DayEntry:
    logged_at: datetime
    food_name: str
    amount_g: float
    nutrients: Nutrients


@dataclass(frozen=True)
class Progress:
    eaten: float
    goal: float
    remaining: float  # negative when over the goal
    percent: float  # may exceed 100


def day_entries(session: Session, day: date) -> list[DayEntry]:
    """Entries logged on `day` (00:00 up to the next 00:00), oldest first."""
    start = datetime.combine(day, time.min)
    statement = (
        select(FoodEntry, Food)
        .join(Food, FoodEntry.food_id == Food.id)
        .where(FoodEntry.logged_at >= start, FoodEntry.logged_at < start + timedelta(days=1))
        .order_by(FoodEntry.logged_at, FoodEntry.id)
    )
    return [
        DayEntry(entry.logged_at, food.name, entry.amount_g, entry_nutrients(food, entry.amount_g))
        for entry, food in session.exec(statement)
    ]


def _progress(eaten: float, goal: float) -> Progress:
    percent = eaten / goal * 100 if goal > 0 else 0.0
    return Progress(eaten=eaten, goal=goal, remaining=goal - eaten, percent=percent)


def compare_to_goal(totals: Nutrients, goal: Goal) -> dict[str, Progress]:
    """Progress per value: keys kcal, protein_g, carbs_g, fat_g."""
    return {
        "kcal": _progress(totals.kcal, goal.kcal),
        "protein_g": _progress(totals.protein_g, goal.protein_g),
        "carbs_g": _progress(totals.carbs_g, goal.carbs_g),
        "fat_g": _progress(totals.fat_g, goal.fat_g),
    }
