"""Request and response shapes of the write endpoints. Field rules give a 422 for malformed
input; the business rules (plausible ranges, duplicates) stay in `core` and give a 400."""

import datetime as dt

from pydantic import BaseModel, ConfigDict, NaiveDatetime


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a misspelled field is an error, not ignored


class NewEntry(Strict):
    food_id: int
    amount_g: float
    logged_at: NaiveDatetime | None = None  # local time; default now


class EntryChange(Strict):
    amount_g: float
    logged_at: NaiveDatetime | None = None  # default: keep the current time


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # built from database rows


class EntryOut(Out):
    id: int
    food_id: int
    logged_at: dt.datetime
    amount_g: float


class FoodValues(Strict):
    name: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class FoodOut(Out):
    id: int
    name: str
    source: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class WeightIn(Strict):
    date: dt.date | None = None  # default today
    weight_kg: float


class WeightOut(Out):
    date: dt.date
    weight_kg: float


class GoalIn(Strict):
    valid_from: dt.date | None = None  # default today
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    target_weight_kg: float | None = None
