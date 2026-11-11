"""SQLModel table definitions.

Nutrition values live only in `Food` (per 100 g). Entries store grams only;
kcal/macros are computed from the food at read time.

Note: SQLModel table models do not run Pydantic validation on init.
Input validation belongs in separate Pydantic models at the input boundary.
"""

import datetime as dt

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class Food(SQLModel, table=True):
    __tablename__ = "foods"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    source: str  # "nevo" | "off" | "manual"
    source_id: str | None = None  # id in the source database, if any
    kcal: float  # per 100 g
    protein_g: float  # per 100 g
    carbs_g: float  # per 100 g
    fat_g: float  # per 100 g


class FoodEntry(SQLModel, table=True):
    __tablename__ = "food_entries"

    id: int | None = Field(default=None, primary_key=True)
    food_id: int = Field(foreign_key="foods.id", index=True)
    logged_at: NaiveDatetime  # local time, stored without timezone (single-user app)
    amount_g: float
    raw_text: str | None = None  # original user input, for debugging/evals


class WeightEntry(SQLModel, table=True):
    __tablename__ = "weight_entries"

    id: int | None = Field(default=None, primary_key=True)
    date: dt.date = Field(unique=True, index=True)  # module alias: field name shadows `date`
    weight_kg: float


class Goal(SQLModel, table=True):
    """A set of daily targets, valid from `valid_from` until the next goal."""

    __tablename__ = "goals"

    id: int | None = Field(default=None, primary_key=True)
    valid_from: dt.date = Field(index=True)
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    target_weight_kg: float | None = None
