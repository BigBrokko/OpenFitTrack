"""Import of the NEVO food composition table (pipe-delimited CSV) into `foods`."""

from pathlib import Path

import pandas as pd
from sqlmodel import Session

from core.foods import ImportResult, upsert_foods
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
    return upsert_foods(session, foods, SOURCE)
