"""Saving, correcting and deleting logged food. No framework imports."""

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


def log_food(session: Session, food_id: int, grams: float, logged_at: datetime) -> FoodEntry:
    """Log one food by id. Raises LookupError for an unknown food, ValueError for grams <= 0."""
    food = session.get(Food, food_id)
    if food is None:
        raise LookupError(f"No food with id {food_id}.")
    (entry,) = save_entries(session, [(food, grams)], logged_at)
    session.refresh(entry)
    return entry


def update_entry(
    session: Session, entry_id: int, amount_g: float, logged_at: datetime | None = None
) -> FoodEntry:
    """Correct the amount (and the time, if given) of a logged entry. The food itself does
    not change (to log another food, delete the entry and log again).

    Raises LookupError for an unknown id and ValueError for an amount of 0 or less.
    """
    if amount_g <= 0:
        raise ValueError("amount in grams must be greater than 0")
    entry = session.get(FoodEntry, entry_id)
    if entry is None:
        raise LookupError(f"No logged entry with id {entry_id}.")
    entry.amount_g = amount_g
    if logged_at is not None:
        entry.logged_at = logged_at
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(session: Session, entry_id: int) -> None:
    """Remove a logged entry. Raises LookupError for an unknown id."""
    entry = session.get(FoodEntry, entry_id)
    if entry is None:
        raise LookupError(f"No logged entry with id {entry_id}.")
    session.delete(entry)
    session.commit()
