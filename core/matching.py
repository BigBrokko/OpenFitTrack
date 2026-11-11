"""Fuzzy search over the `foods` table.

Used both for manual search and for linking parsed items to database foods.
"""

import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, utils
from sqlmodel import Session, select

from core.models import Food

# NEVO names put the main food first ("Kwark magere", "Ei kippen- rauw gem"), so a name
# whose first word starts with a query word is ranked above names that merely contain it.
FIRST_WORD_BONUS = 10


@dataclass(frozen=True)
class FoodMatch:
    food: Food
    score: float  # 0-100


def _normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return utils.default_process(without_accents)


def search_foods(
    session: Session, query: str, limit: int = 5, min_score: float = 60
) -> list[FoodMatch]:
    """Return the best matching foods for `query`, best first.

    Word order, case and accents are ignored. Ties are broken by the shorter name.
    """
    query_tokens = _normalize(query).split()
    if not query_tokens:
        return []
    normalized_query = " ".join(query_tokens)

    ranked: list[tuple[float, int, Food]] = []
    for food in session.exec(select(Food)).all():
        name_tokens = _normalize(food.name).split()
        if not name_tokens:
            continue
        base = fuzz.token_set_ratio(normalized_query, " ".join(name_tokens))
        if base < min_score:
            continue
        bonus = FIRST_WORD_BONUS if any(name_tokens[0].startswith(t) for t in query_tokens) else 0
        ranked.append((base + bonus, len(food.name), food))

    ranked.sort(key=lambda r: (-r[0], r[1]))
    return [FoodMatch(food=food, score=min(100.0, score)) for score, _, food in ranked[:limit]]
