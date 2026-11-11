"""Creating foods by hand (source "manual")."""

from sqlmodel import Session, func, select

from core.models import Food

MAX_MACROS_PER_100G = 100


def add_manual_food(
    session: Session,
    name: str,
    kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
) -> Food:
    """Create a food from values per 100 g. Raises ValueError for invalid input."""
    name = name.strip()
    if not name:
        raise ValueError("Name must not be empty.")
    if min(kcal, protein_g, carbs_g, fat_g) < 0:
        raise ValueError("Values must not be negative.")
    if protein_g + carbs_g + fat_g > MAX_MACROS_PER_100G:
        raise ValueError("Protein, carbs and fat together cannot exceed 100 g per 100 g.")

    duplicate = session.exec(
        select(Food).where(Food.source == "manual", func.lower(Food.name) == name.lower())
    ).first()
    if duplicate is not None:
        raise ValueError(f"A manual food named '{duplicate.name}' already exists.")

    food = Food(
        name=name,
        source="manual",
        kcal=kcal,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    session.add(food)
    session.commit()
    session.refresh(food)
    return food
