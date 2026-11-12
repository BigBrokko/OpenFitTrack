"""Fill a database with dummy weights and a goal, to try the app without real data.

Writes to DATABASE_URL (default: openfittrack.db), so point it at a throwaway database
if you do not want demo data mixed with your own. There is no delete function yet.

Usage: uv run python scripts/seed_demo_data.py
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from sqlmodel import Session  # noqa: E402

from core.db import create_db, get_current_goal, get_engine  # noqa: E402
from core.goals import set_goal  # noqa: E402
from core.weight import log_weight  # noqa: E402

DAYS = 70
START_WEIGHT_KG = 86.0
LOSS_PER_WEEK_KG = 0.4
TARGET_WEIGHT_KG = 80.0


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

    print(f"Demo data: {logged} weights over {DAYS} days (existing days were replaced).")


if __name__ == "__main__":
    main()
