"""Shapes of the tool answers. Field descriptions are shown to the AI model."""

import datetime as dt

from pydantic import BaseModel, Field


class NutrientValues(BaseModel):
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class GoalInfo(BaseModel):
    valid_from: dt.date = Field(description="The goal applies from this date until the next one.")
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    target_weight_kg: float | None = None


class ProgressItem(BaseModel):
    eaten: float
    goal: float
    remaining: float = Field(description="Goal minus eaten. Negative means over the goal.")
    percent: float = Field(description="Eaten as a percentage of the goal. May exceed 100.")


class LoggedEntry(BaseModel):
    time: str = Field(description="Local time, HH:MM.")
    food: str
    amount_g: float
    nutrients: NutrientValues = Field(description="For this amount, not per 100 g.")


class DaySummary(BaseModel):
    date: dt.date
    totals: NutrientValues
    goal: GoalInfo | None = Field(description="The goal that applied on this day, if any.")
    progress: dict[str, ProgressItem] | None = Field(
        description="Keys kcal, protein_g, carbs_g, fat_g vs the goal; null without a goal."
    )
    entries: list[LoggedEntry]
    note: str | None = None


class DayTotals(BaseModel):
    date: dt.date
    totals: NutrientValues


class PeriodSummary(BaseModel):
    start_date: dt.date
    end_date: dt.date
    days_in_period: int
    days_logged: int = Field(description="Days with at least one logged entry.")
    daily: list[DayTotals] = Field(description="Only days that have logged food, oldest first.")
    average_per_logged_day: NutrientValues | None = Field(
        description="Mean over the logged days only. Unlogged days are not counted as zero."
    )
    goal_on_end_date: GoalInfo | None = None
    average_vs_goal: dict[str, ProgressItem] | None = Field(
        description="The average per logged day compared to the goal on the end date."
    )
    note: str | None = None


class WeightPoint(BaseModel):
    date: dt.date
    weight_kg: float
    trend_kg: float = Field(description="Exponential moving average (half-life 7 days).")


class WeightTrend(BaseModel):
    points: list[WeightPoint] = Field(description="Measurements in the requested window.")
    measurements_total: int = Field(description="All measurements ever logged.")
    latest_weight_kg: float | None
    latest_trend_kg: float | None
    trend_change_7d_kg: float | None = Field(
        description="Change of the trend over the last 7 days; null without enough history."
    )
    target_weight_kg: float | None = Field(description="From the goal that applies today.")


class GoalsInfo(BaseModel):
    current: GoalInfo | None = Field(description="The goal that applies today.")
    history: list[GoalInfo] = Field(description="All goals, newest first.")


class FoodCandidate(BaseModel):
    name: str
    source: str = Field(description="Where the food came from, e.g. manual or an import name.")
    kcal: float = Field(description="Per 100 g.")
    protein_g: float = Field(description="Per 100 g.")
    carbs_g: float = Field(description="Per 100 g.")
    fat_g: float = Field(description="Per 100 g.")
    score: float = Field(description="Match quality, 0-100.")


class FoodSearchResult(BaseModel):
    query: str
    results: list[FoodCandidate] = Field(description="Best match first.")
