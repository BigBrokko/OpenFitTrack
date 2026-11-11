"""Nutrition calculations. Plain Python: the LLM never produces nutrition values."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from core.models import Food, FoodEntry


@dataclass(frozen=True)
class Nutrients:
    kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0

    def __add__(self, other: "Nutrients") -> "Nutrients":
        return Nutrients(
            kcal=self.kcal + other.kcal,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
        )

    @classmethod
    def zero(cls) -> "Nutrients":
        return cls()


def entry_nutrients(food: Food, amount_g: float) -> Nutrients:
    """Nutrients for `amount_g` grams of `food` (food values are per 100 g)."""
    if amount_g < 0:
        raise ValueError(f"amount_g must be >= 0, got {amount_g}")
    factor = amount_g / 100
    return Nutrients(
        kcal=food.kcal * factor,
        protein_g=food.protein_g * factor,
        carbs_g=food.carbs_g * factor,
        fat_g=food.fat_g * factor,
    )


def day_totals(session: Session, day: date) -> Nutrients:
    """Sum of all entries logged on `day` (local time, 00:00 up to the next 00:00)."""
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    statement = (
        select(FoodEntry, Food)
        .join(Food, FoodEntry.food_id == Food.id)
        .where(FoodEntry.logged_at >= start, FoodEntry.logged_at < end)
    )
    total = Nutrients.zero()
    for entry, food in session.exec(statement):
        total += entry_nutrients(food, entry.amount_g)
    return total
