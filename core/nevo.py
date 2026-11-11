"""Import of the NEVO food composition table (pipe-delimited CSV) into `foods`."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from core.models import Food

SOURCE = "nevo"
KJ_PER_KCAL = 4.184

COL_CODE = "NEVO-code"
COL_NAME = "Voedingsmiddelnaam/Dutch food name"
COL_QUANTITY = "Hoeveelheid/Quantity"
COL_KJ = "ENERCJ (kJ)"
COL_KCAL = "ENERCC (kcal)"
COL_PROTEIN = "PROT (g)"
COL_CARBS = "CHO (g)"
COL_FAT = "FAT (g)"

# Foods are stored per 100 g. NEVO also has a few "per 100ml" rows (baby formula);
# converting those to grams would need a density, so they are skipped.
PER_100G = "per 100g"


@dataclass
class ImportResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0


def _to_number(series: pd.Series) -> pd.Series:
    """Parse NEVO numbers, which use a decimal comma. Unparseable values become NaN."""
    return pd.to_numeric(series.str.replace(",", ".", regex=False), errors="coerce")


def load_nevo(path: str | Path) -> tuple[list[Food], int]:
    """Read a NEVO CSV and return (foods, number of skipped rows).

    Rows are skipped when they are not per 100 g or when a required value is missing.
    kcal is taken from the file; only if it is missing is it derived from kJ.
    """
    df = pd.read_csv(path, sep="|", encoding="utf-8", dtype=str)
    total = len(df)

    df = df[df[COL_QUANTITY].str.strip() == PER_100G].copy()

    kcal = _to_number(df[COL_KCAL])
    df["kcal"] = kcal.fillna(_to_number(df[COL_KJ]) / KJ_PER_KCAL)
    df["protein_g"] = _to_number(df[COL_PROTEIN])
    df["carbs_g"] = _to_number(df[COL_CARBS])
    df["fat_g"] = _to_number(df[COL_FAT])

    df = df.dropna(subset=["kcal", "protein_g", "carbs_g", "fat_g", COL_NAME, COL_CODE])

    foods = [
        Food(
            name=row[COL_NAME].strip(),
            source=SOURCE,
            source_id=str(row[COL_CODE]).strip(),
            kcal=float(row["kcal"]),
            protein_g=float(row["protein_g"]),
            carbs_g=float(row["carbs_g"]),
            fat_g=float(row["fat_g"]),
        )
        for _, row in df.iterrows()
    ]
    return foods, total - len(foods)


def import_foods(session: Session, foods: list[Food]) -> ImportResult:
    """Upsert NEVO foods on (source, source_id). Foods from other sources are untouched."""
    existing = {
        f.source_id: f for f in session.exec(select(Food).where(Food.source == SOURCE)).all()
    }
    result = ImportResult()
    for food in foods:
        current = existing.get(food.source_id)
        if current is None:
            session.add(food)
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
