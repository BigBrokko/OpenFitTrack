"""Fill a database with dummy foods, meals, weights and a goal, to try the app without real data.

Writes to DATABASE_URL (default: openfittrack.db), so point it at a throwaway database
if you do not want demo data mixed with your own. There is no delete function yet.

Usage: uv run python scripts/seed_demo_data.py
"""

import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from core.db import create_db, get_current_goal, get_engine  # noqa: E402
from core.foods import add_manual_food  # noqa: E402
from core.goals import set_goal  # noqa: E402
from core.meal_log import save_entries  # noqa: E402
from core.models import Food, FoodEntry  # noqa: E402
from core.weight import log_weight  # noqa: E402

DAYS = 70
START_WEIGHT_KG = 86.0
LOSS_PER_WEEK_KG = 0.4
TARGET_WEIGHT_KG = 80.0
MEAL_DAYS = 7
FOODS = {  # name: (kcal, protein, carbs, fat) per 100 g
    "Kwark volle": (118, 7.5, 3.6, 8),
    "Banaan": (92, 1.1, 20, 0.3),
    "Havermout": (372, 13.5, 58.7, 7),
    "Pindakaas": (650, 25, 12, 50),
    "Volkorenbrood": (230, 9, 41, 2.5),
}


def seed_meals(session: Session, rng: random.Random, today: date) -> int:
    """A few foods and a week of meals. Skipped when the database already has entries."""
    if session.exec(select(FoodEntry)).first() is not None:
        return 0
    foods = {}
    for name, (kcal, protein, carbs, fat) in FOODS.items():
        existing = session.exec(select(Food).where(Food.name == name)).first()
        foods[name] = existing or add_manual_food(session, name, kcal, protein, carbs, fat)

    meals = [  # (hour, [(food, typical grams)])
        (8, [("Havermout", 60), ("Banaan", 100), ("Kwark volle", 150)]),
        (12, [("Volkorenbrood", 80), ("Pindakaas", 25)]),
        (19, [("Kwark volle", 200), ("Banaan", 120)]),
    ]
    logged = 0
    for offset in range(MEAL_DAYS):
        day = today - timedelta(days=offset)
        for hour, items in meals:
            if offset == 0 and hour > datetime.now().hour:
                continue  # today only has the meals that already happened
            when = datetime.combine(day, time(hour, rng.choice([0, 15, 30, 45])))
            entries = [(foods[name], round(grams * rng.uniform(0.8, 1.2))) for name, grams in items]
            save_entries(session, entries, when)
            logged += len(entries)
    return logged


def main() -> None:
    load_dotenv()
    rng = random.Random(42)  # fixed seed: the same demo data every time
    today = date.today()

    engine = get_engine()
    create_db(engine)
    with Session(engine) as session:
        logged = 0
        for offset in range(DAYS, -1, -1):
            if rng.random() < 0.25:  # skip some days, like real life
                continue
            weight = START_WEIGHT_KG - LOSS_PER_WEEK_KG * (DAYS - offset) / 7 + rng.gauss(0, 0.6)
            log_weight(session, today - timedelta(days=offset), round(weight, 1))
            logged += 1

        if get_current_goal(session, today) is None:
            set_goal(session, today - timedelta(days=DAYS), 2200, 150, 250, 70, TARGET_WEIGHT_KG)

        meals = seed_meals(session, rng, today)

    print(f"Demo data: {logged} weights over {DAYS} days (existing days were replaced).")
    print(f"           {meals} logged foods over the last {MEAL_DAYS} days.")


if __name__ == "__main__":
    main()
