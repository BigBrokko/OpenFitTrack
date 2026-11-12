"""Managing foods: creating and editing your own (source "manual"), and bulk upserts."""

from dataclasses import dataclass

from sqlmodel import Session, func, select

from core.models import Food

MAX_MACROS_PER_100G = 100
MANUAL = "manual"


@dataclass
class ImportResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0


def _validated_name(name: str, kcal: float, protein_g: float, carbs_g: float, fat_g: float) -> str:
    """Check values per 100 g and return the stripped name. Raises ValueError."""
    name = name.strip()
    if not name:
        raise ValueError("Name must not be empty.")
    if min(kcal, protein_g, carbs_g, fat_g) < 0:
        raise ValueError("Values must not be negative.")
    if protein_g + carbs_g + fat_g > MAX_MACROS_PER_100G:
        raise ValueError("Protein, carbs and fat together cannot exceed 100 g per 100 g.")
    return name


def _check_no_duplicate(session: Session, name: str, ignore_id: int | None = None) -> None:
    statement = select(Food).where(Food.source == MANUAL, func.lower(Food.name) == name.lower())
    duplicate = session.exec(statement).first()
    if duplicate is not None and duplicate.id != ignore_id:
        raise ValueError(f"A manual food named '{duplicate.name}' already exists.")


def add_manual_food(
    session: Session,
    name: str,
    kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
) -> Food:
    """Create a food from values per 100 g. Raises ValueError for invalid input."""
    name = _validated_name(name, kcal, protein_g, carbs_g, fat_g)
    _check_no_duplicate(session, name)

    food = Food(
        name=name,
        source=MANUAL,
        kcal=kcal,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def list_manual_foods(session: Session) -> list[Food]:
    """Your own foods, sorted by name."""
    statement = select(Food).where(Food.source == MANUAL).order_by(func.lower(Food.name))
    return list(session.exec(statement).all())


def update_manual_food(
    session: Session,
    food_id: int,
    name: str,
    kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
) -> Food:
    """Change one of your own foods. Logged entries pick up the new values automatically,
    because they only store grams. Raises ValueError for invalid input or a food that is
    not manual (imported foods are not edited here).
    """
    food = session.get(Food, food_id)
    if food is None or food.source != MANUAL:
        raise ValueError("Only your own (manual) foods can be edited.")
    name = _validated_name(name, kcal, protein_g, carbs_g, fat_g)
    _check_no_duplicate(session, name, ignore_id=food_id)

    food.name = name
    food.kcal = kcal
    food.protein_g = protein_g
    food.carbs_g = carbs_g
    food.fat_g = fat_g
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def _key(food: Food) -> str:
    """Identity of a food within its source: the source id, else the lowercase name."""
    return food.source_id if food.source_id else f"name:{food.name.lower()}"


def upsert_foods(session: Session, foods: list[Food], source: str) -> ImportResult:
    """Add new foods and update existing ones of one source. Other sources stay untouched.

    A food is the same food when it has the same source id, or, without a source id, the
    same name (ignoring case). Running the same import twice therefore adds nothing.
    """
    if any(food.source != source for food in foods):
        raise ValueError(f"All foods must have source '{source}'.")

    existing = {_key(f): f for f in session.exec(select(Food).where(Food.source == source)).all()}
    result = ImportResult()
    for food in foods:
        current = existing.get(_key(food))
        if current is None:
            session.add(food)
            existing[_key(food)] = food  # a repeat of the same food later in the file updates it
            result.added += 1
        else:
            current.name = food.name
            current.kcal = food.kcal
            current.protein_g = food.protein_g
            current.carbs_g = food.carbs_g
            current.fat_g = food.fat_g
            result.updated += 1
    session.commit()
    return result
