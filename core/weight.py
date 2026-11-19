"""Weight entries and the EMA trend line."""

from datetime import date

import pandas as pd
from sqlmodel import Session, select

from core.models import WeightEntry

MIN_WEIGHT_KG = 20
MAX_WEIGHT_KG = 400
DEFAULT_HALFLIFE_DAYS = 7.0


def log_weight(session: Session, day: date, weight_kg: float) -> WeightEntry:
    """Save the weight for `day`. A measurement already on that day is replaced.

    Raises ValueError when the weight is outside the plausible range.
    """
    if not MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG:
        raise ValueError(f"Weight must be between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG} kg.")

    entry = session.exec(select(WeightEntry).where(WeightEntry.date == day)).first()
    if entry is None:
        entry = WeightEntry(date=day, weight_kg=weight_kg)
    entry.weight_kg = weight_kg
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def list_weights(session: Session) -> list[WeightEntry]:
    """All measurements, oldest first."""
    return list(session.exec(select(WeightEntry).order_by(WeightEntry.date)).all())


def weight_trend(
    entries: list[WeightEntry], halflife_days: float = DEFAULT_HALFLIFE_DAYS
) -> pd.DataFrame:
    """Measurements plus an exponential moving average, as columns date, weight_kg, trend_kg.

    The average is time-aware: a measurement's influence halves every `halflife_days`
    days, so gaps between measurements do not distort the trend. The first trend value
    equals the first measurement.
    """
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime([e.date for e in entries]),
            "weight_kg": [e.weight_kg for e in entries],
        }
    ).sort_values("date", ignore_index=True)
    if frame.empty:
        frame["trend_kg"] = pd.Series(dtype=float)
        return frame
    frame["trend_kg"] = (
        frame["weight_kg"]
        .ewm(halflife=pd.Timedelta(days=halflife_days), times=frame["date"])
        .mean()
    )
    return frame


def trend_change(trend: pd.DataFrame, days: int = 7) -> float | None:
    """Change of the trend over the last `days` days, or None without a measurement that old."""
    if trend.empty:
        return None
    latest = trend.iloc[-1]
    older = trend[trend["date"] <= latest["date"] - pd.Timedelta(days=days)]
    if older.empty:
        return None
    return float(latest["trend_kg"] - older.iloc[-1]["trend_kg"])
