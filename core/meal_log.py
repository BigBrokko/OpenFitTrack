"""Saving logged food. No Streamlit here: the UI only calls these functions."""

from datetime import datetime

from sqlmodel import Session

from core.models import Food, FoodEntry


def save_entries(
    session: Session,
    entries: list[tuple[Food, float]],
    logged_at: datetime,
) -> list[FoodEntry]:
    """Store (food, grams) pairs as FoodEntry rows."""
    if any(grams <= 0 for _, grams in entries):
        raise ValueError("amount in grams must be greater than 0")

    saved = [
        FoodEntry(food_id=food.id, logged_at=logged_at, amount_g=grams) for food, grams in entries
    ]
    session.add_all(saved)
    session.commit()
    return saved
