"""Turn a parsed meal into proposed entries, and save confirmed entries.

No Streamlit here: the UI only calls these functions.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from core.matching import FoodMatch, search_foods
from core.models import Food, FoodEntry
from core.parsing import ParsedItem, ParsedMeal

# Grams per unit and whether that number is only a rough guess. Weights of pieces,
# slices etc. differ per food (a banana is not an egg), so guesses are flagged and the
# user checks them on the confirmation screen. ml/l are treated 1:1 as grams, which is
# close for water and milk but not for oil or honey.
UNIT_GRAMS: dict[str, tuple[float, bool]] = {
    "g": (1, False),
    "kg": (1000, False),
    "ml": (1, False),
    "l": (1000, False),
    "tbsp": (15, True),
    "tsp": (5, True),
    "cup": (150, True),
    "slice": (30, True),
    "piece": (100, True),
    "portion": (100, True),
}


@dataclass
class ProposedEntry:
    item: ParsedItem
    candidates: list[FoodMatch]  # best match first; empty when nothing was found
    amount_g: float
    estimated: bool  # True when amount_g is a rough guess the user should check


def unit_to_grams(quantity: float, unit: str) -> tuple[float, bool]:
    """Convert a parsed quantity to grams. Returns (grams, is_rough_estimate)."""
    grams_per_unit, estimated = UNIT_GRAMS[unit]
    return quantity * grams_per_unit, estimated


def propose_entries(
    session: Session, meal: ParsedMeal, candidates_per_item: int = 5
) -> list[ProposedEntry]:
    """Look up database candidates and a gram amount for every parsed item."""
    proposals = []
    for item in meal.items:
        grams, estimated = unit_to_grams(item.quantity, item.unit)
        candidates = search_foods(session, item.name, limit=candidates_per_item)
        proposals.append(ProposedEntry(item, candidates, grams, estimated))
    return proposals


def save_entries(
    session: Session,
    entries: list[tuple[Food, float]],
    logged_at: datetime,
    raw_text: str | None = None,
) -> list[FoodEntry]:
    """Store confirmed (food, grams) pairs as FoodEntry rows."""
    if any(grams <= 0 for _, grams in entries):
        raise ValueError("amount in grams must be greater than 0")

    saved = [
        FoodEntry(food_id=food.id, logged_at=logged_at, amount_g=grams, raw_text=raw_text)
        for food, grams in entries
    ]
    session.add_all(saved)
    session.commit()
    return saved
