from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from core.db import create_db, get_current_goal
from core.models import Food, FoodEntry, Goal, WeightEntry


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    create_db(engine)
    with Session(engine) as session:
        yield session


def make_food(name: str = "Kwark") -> Food:
    return Food(name=name, source="manual", kcal=60.0, protein_g=10.0, carbs_g=4.0, fat_g=0.2)


def test_food_roundtrip(session):
    session.add(make_food())
    session.commit()

    food = session.exec(select(Food).where(Food.name == "Kwark")).one()
    assert food.id is not None
    assert food.kcal == 60.0
    assert food.source_id is None


def test_food_entry_references_food(session):
    food = make_food()
    session.add(food)
    session.commit()

    entry = FoodEntry(
        food_id=food.id,
        logged_at=datetime(2026, 1, 5, 8, 30),
        amount_g=200.0,
        raw_text="200g kwark",
    )
    session.add(entry)
    session.commit()

    saved = session.exec(select(FoodEntry)).one()
    assert saved.food_id == food.id
    assert saved.amount_g == 200.0
    assert saved.raw_text == "200g kwark"


def test_weight_date_is_unique(session):
    session.add(WeightEntry(date=date(2026, 1, 5), weight_kg=80.0))
    session.commit()

    session.add(WeightEntry(date=date(2026, 1, 5), weight_kg=79.5))
    with pytest.raises(IntegrityError):
        session.commit()


def test_current_goal_uses_latest_valid_from(session):
    session.add(Goal(valid_from=date(2026, 1, 1), kcal=2500, protein_g=150, carbs_g=300, fat_g=70))
    session.add(Goal(valid_from=date(2026, 3, 1), kcal=2200, protein_g=160, carbs_g=240, fat_g=65))
    session.commit()

    assert get_current_goal(session, date(2025, 12, 31)) is None
    assert get_current_goal(session, date(2026, 2, 15)).kcal == 2500
    assert get_current_goal(session, date(2026, 3, 1)).kcal == 2200
    assert get_current_goal(session, date(2026, 6, 1)).kcal == 2200
