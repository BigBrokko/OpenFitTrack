"""Import foods from any CSV file, using a mapping of columns to food fields.

Everything is read as "per 100 g". The caller (the importer page) makes the user confirm
that, because a file in "per serving" or "per 100 ml" would give silently wrong values.
"""

import csv
import io
import math
import re
import unicodedata
from dataclasses import dataclass

import pandas as pd

from core.foods import MANUAL
from core.models import Food

KJ_PER_KCAL = 4.184
MAX_KCAL_PER_100G = 950  # pure fat is ~900; more usually means a kJ column was picked as kcal
MACRO_TOLERANCE_G = 1.0  # source tables round, so 100.4 g of macros per 100 g is accepted
CANDIDATE_DELIMITERS = [",", ";", "|", "\t"]
FIELDS = ("name", "kcal", "kj", "protein_g", "carbs_g", "fat_g", "source_id")


@dataclass(frozen=True)
class CsvTable:
    frame: pd.DataFrame  # all cells as text
    delimiter: str
    encoding: str


@dataclass(frozen=True)
class ColumnMapping:
    """Names of the CSV columns. kcal or kj is required (kJ is converted when kcal is empty)."""

    name: str
    protein_g: str
    carbs_g: str
    fat_g: str
    kcal: str | None = None
    kj: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class SkippedRow:
    row: int  # line number in the file, counting the header as line 1
    reason: str


@dataclass(frozen=True)
class ParsedFoods:
    foods: list[Food]
    skipped: list[SkippedRow]


# --- Reading -----------------------------------------------------------------


def _detect_delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    best, best_fields = ",", 1
    for delimiter in CANDIDATE_DELIMITERS:
        fields = len(next(csv.reader([first_line], delimiter=delimiter), []))
        if fields > best_fields:
            best, best_fields = delimiter, fields
    return best


def read_csv_table(data: bytes) -> CsvTable:
    """Decode a CSV file and detect its delimiter. Raises ValueError for unusable files."""
    if not data.strip():
        raise ValueError("The file is empty.")
    try:
        text, encoding = data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = data.decode("latin-1"), "latin-1"

    delimiter = _detect_delimiter(text)
    try:
        frame = pd.read_csv(
            io.StringIO(text),
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
            on_bad_lines="skip",
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(f"Could not read the file as CSV: {error}") from error
    frame.columns = [str(column).strip() for column in frame.columns]
    return CsvTable(frame=frame, delimiter=delimiter, encoding=encoding)


def parse_number(text: str) -> float | None:
    """Parse "12", "12.5", "12,5" or "1.234,5". Anything else (empty, "tr", "<0.1") is None."""
    cleaned = text.strip().replace(" ", "").replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):  # 1.234,5: comma is the decimal mark
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:  # 1,234.5
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


# --- Column guessing ---------------------------------------------------------

# Header words (Dutch and English) per field, and words that rule a column out.
_SYNONYMS = {
    "name": {"name", "naam", "description", "omschrijving", "product", "voedingsmiddelnaam"},
    "kcal": {"kcal", "calories", "calorieen"},
    "kj": {"kj", "kilojoule", "kilojoules"},
    "protein_g": {"protein", "proteins", "eiwit", "eiwitten", "prot"},
    "carbs_g": {"carbohydrate", "carbohydrates", "carbs", "koolhydraten", "koolhydraat", "cho"},
    "fat_g": {"fat", "fats", "vet", "vetten", "lipid"},
    "source_id": {"id", "code", "barcode", "ean"},
}
_EXCLUDED = {
    "name": {"group", "groep", "code", "id", "category", "categorie", "scientific", "latin"},
    "protein_g": {"plant", "animal", "vegetable"},
    "carbs_g": {"sugar", "sugars", "fiber", "fibre", "starch", "vezel", "polyols", "suiker"},
    "fat_g": {"saturated", "trans", "unsaturated", "monounsaturated", "polyunsaturated"}
    | {"verzadigd", "omega"},
}


def _tokens(header: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", header.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", plain))


def guess_mapping(columns: list[str]) -> dict[str, str | None]:
    """Suggest a column for every field from the header names. None when nothing fits."""
    guess: dict[str, str | None] = {}
    used: set[str] = set()
    for field in FIELDS:
        guess[field] = None
        for column in columns:
            tokens = _tokens(column)
            if column in used or not tokens & _SYNONYMS[field]:
                continue
            if tokens & _EXCLUDED.get(field, set()):
                continue
            guess[field] = column
            used.add(column)
            break
    return guess


# --- Converting --------------------------------------------------------------


def foods_from_table(table: pd.DataFrame, mapping: ColumnMapping, source: str) -> ParsedFoods:
    """Turn rows into foods. Invalid rows are skipped and reported, never silently fixed.

    Raises ValueError for an unusable mapping or source name.
    """
    source = source.strip()
    if not source:
        raise ValueError("Source name must not be empty.")
    if source.lower() == MANUAL:
        raise ValueError(f"'{MANUAL}' is reserved for foods you create yourself.")
    if mapping.kcal is None and mapping.kj is None:
        raise ValueError("Choose a kcal column (or a kJ column).")

    chosen = [c for c in (*_mapping_columns(mapping),) if c is not None]
    missing = [c for c in chosen if c not in table.columns]
    if missing:
        raise ValueError(f"Columns not in the file: {', '.join(missing)}")

    foods: list[Food] = []
    skipped: list[SkippedRow] = []
    for line, row in enumerate(table.to_dict("records"), start=2):
        food, reason = _food_from_row(row, mapping, source)
        if food is not None:
            foods.append(food)
        else:
            skipped.append(SkippedRow(line, reason))
    return ParsedFoods(foods=foods, skipped=skipped)


def _mapping_columns(mapping: ColumnMapping) -> tuple[str | None, ...]:
    return (
        mapping.name,
        mapping.protein_g,
        mapping.carbs_g,
        mapping.fat_g,
        mapping.kcal,
        mapping.kj,
        mapping.source_id,
    )


def _food_from_row(row: dict, mapping: ColumnMapping, source: str) -> tuple[Food | None, str]:
    name = str(row[mapping.name]).strip()
    if not name:
        return None, "empty name"

    values = {}
    for label, column in (
        ("protein", mapping.protein_g),
        ("carbs", mapping.carbs_g),
        ("fat", mapping.fat_g),
    ):
        number = parse_number(str(row[column]))
        if number is None:
            return None, f"missing or invalid {label}"
        values[label] = number

    kcal = parse_number(str(row[mapping.kcal])) if mapping.kcal else None
    if kcal is None and mapping.kj:
        kj = parse_number(str(row[mapping.kj]))
        kcal = kj / KJ_PER_KCAL if kj is not None else None
    if kcal is None:
        return None, "missing or invalid kcal"

    if min(kcal, *values.values()) < 0:
        return None, "negative value"
    if kcal > MAX_KCAL_PER_100G:
        return None, f"kcal above {MAX_KCAL_PER_100G} per 100 g (is this column kJ?)"
    if sum(values.values()) > 100 + MACRO_TOLERANCE_G:
        return None, "protein, carbs and fat add up to more than 100 g per 100 g"

    source_id = str(row[mapping.source_id]).strip() if mapping.source_id else ""
    food = Food(
        name=name,
        source=source,
        source_id=source_id or None,
        kcal=kcal,
        protein_g=values["protein"],
        carbs_g=values["carbs"],
        fat_g=values["fat"],
    )
    return food, ""
