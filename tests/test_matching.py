from core.matching import search_foods
from core.models import Food


def add_foods(session, *names: str) -> None:
    for name in names:
        session.add(Food(name=name, source="manual", kcal=1, protein_g=1, carbs_g=1, fat_g=1))
    session.commit()


def names(matches) -> list[str]:
    return [m.food.name for m in matches]


def test_exact_name_ranks_first(session):
    add_foods(session, "Banaan bak- rijp rauw", "Banaan", "Ananas")

    matches = search_foods(session, "banaan")

    assert matches[0].food.name == "Banaan"
    assert matches[0].score == 100


def test_word_order_does_not_matter(session):
    add_foods(session, "Kwark magere", "Kwark volle", "Melk magere")

    assert names(search_foods(session, "magere kwark"))[0] == "Kwark magere"


def test_ignores_case_and_accents(session):
    add_foods(session, "Crème fraîche", "Kwark")

    assert names(search_foods(session, "CREME fraiche"))[0] == "Crème fraîche"


def test_main_food_beats_ingredient_in_other_dish(session):
    add_foods(session, "Bami goreng z ei", "Ei kippen- rauw gem")

    assert names(search_foods(session, "ei"))[0] == "Ei kippen- rauw gem"


def test_tie_prefers_shorter_name(session):
    add_foods(session, "Kwark vruchten- halfvolle", "Kwark volle")

    assert names(search_foods(session, "kwark")) == ["Kwark volle", "Kwark vruchten- halfvolle"]


def test_limit_is_respected(session):
    add_foods(session, *(f"Kwark soort {i}" for i in range(10)))

    assert len(search_foods(session, "kwark", limit=3)) == 3


def test_unrelated_query_returns_nothing(session):
    add_foods(session, "Kwark magere", "Banaan")

    assert search_foods(session, "xyzqw") == []


def test_empty_query_returns_nothing(session):
    add_foods(session, "Kwark magere")

    assert search_foods(session, "") == []
    assert search_foods(session, "   ") == []


def test_score_is_capped_at_100(session):
    add_foods(session, "Ei kippen- rauw gem")

    assert search_foods(session, "ei")[0].score == 100
