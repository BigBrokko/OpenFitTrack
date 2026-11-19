"""Statistics over a period of days."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from core.models import Food, FoodEntry
from core.nutrition import Nutrients, entry_nutrients

MAX_PERIOD_DAYS = 366


@dataclass(frozen=True)
class PeriodStats:
    start: date
    end: date
    daily: list[tuple[date, Nutrients]]  # only days with at least one entry, oldest first

    @property
    def days_in_period(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def days_logged(self) -> int:
        return len(self.daily)

    @property
    def average_per_logged_day(self) -> Nutrients | None:
        """Mean over days with logged food. Days without entries are not counted as zero:
        no entries usually means "not logged", not "ate nothing"."""
        if not self.daily:
            return None
        total = Nutrients.zero()
        for _, nutrients in self.daily:
            total += nutrients
        n = len(self.daily)
        return Nutrients(total.kcal / n, total.protein_g / n, total.carbs_g / n, total.fat_g / n)


def period_stats(session: Session, start: date, end: date) -> PeriodStats:
    """Daily totals from `start` to `end`, both included. Raises ValueError for a bad range."""
    if end < start:
        raise ValueError("end date must not be before the start date.")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        raise ValueError(f"A period can be at most {MAX_PERIOD_DAYS} days.")

    first = datetime.combine(start, time.min)
    last = datetime.combine(end, time.min) + timedelta(days=1)
    statement = (
        select(FoodEntry, Food)
        .join(Food, FoodEntry.food_id == Food.id)
        .where(FoodEntry.logged_at >= first, FoodEntry.logged_at < last)
    )
    totals: dict[date, Nutrients] = {}
    for entry, food in session.exec(statement):
        day = entry.logged_at.date()
        totals[day] = totals.get(day, Nutrients.zero()) + entry_nutrients(food, entry.amount_g)
    return PeriodStats(start=start, end=end, daily=sorted(totals.items()))
