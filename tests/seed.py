"""A small week of data shared by the MCP server tests and the API tests."""

from datetime import date, datetime

from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.foods import add_manual_food
from core.goals import set_goal
from core.models import FoodEntry
from core.weight import log_weight

TODAY = date(2026, 1, 12)


def seed(engine: Engine) -> Engine:
    """Kwark on three days (6, 8 and 12 January), three weights and one goal."""
    with Session(engine) as session:
        kwark = add_manual_food(session, "Kwark magere", 51, 8.4, 3.8, 0)
        add_manual_food(session, "Banaan", 90, 1, 20, 0.3)
        for day, grams in [(6, 200), (8, 200), (12, 100)]:
            session.add(
                FoodEntry(food_id=kwark.id, logged_at=datetime(2026, 1, day, 8), amount_g=grams)
            )
        session.commit()
        set_goal(session, date(2026, 1, 1), 2000, 120, 200, 60, target_weight_kg=78)
        for day, kg in [(1, 82.0), (8, 81.0), (12, 80.5)]:
            log_weight(session, date(2026, 1, day), kg)
    return engine
