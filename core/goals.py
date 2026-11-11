"""Daily goals. Every change is a new row valid from a date; old rows are kept."""

from datetime import date

from sqlmodel import Session, select

from core.models import Goal


def set_goal(
    session: Session,
    valid_from: date,
    kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    target_weight_kg: float | None = None,
) -> Goal:
    """Save a goal valid from `valid_from`. A goal that already starts on that date is replaced.

    Raises ValueError for invalid values.
    """
    if kcal <= 0:
        raise ValueError("kcal must be greater than 0.")
    if min(protein_g, carbs_g, fat_g) < 0:
        raise ValueError("Protein, carbs and fat must not be negative.")
    if target_weight_kg is not None and target_weight_kg <= 0:
        raise ValueError("Target weight must be greater than 0.")

    goal = session.exec(select(Goal).where(Goal.valid_from == valid_from)).first()
    if goal is None:
        goal = Goal(
            valid_from=valid_from, kcal=kcal, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g
        )
    goal.kcal = kcal
    goal.protein_g = protein_g
    goal.carbs_g = carbs_g
    goal.fat_g = fat_g
    goal.target_weight_kg = target_weight_kg
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


def list_goals(session: Session) -> list[Goal]:
    """All goals, newest first."""
    return list(session.exec(select(Goal).order_by(Goal.valid_from.desc())).all())
