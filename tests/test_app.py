"""Streamlit smoke tests for both logging pages, run against a temporary database."""

from pathlib import Path

import pytest
from sqlmodel import Session, select
from streamlit.testing.v1 import AppTest

from core.db import create_db, get_engine
from core.models import Food, FoodEntry
from core.parsing import ParsedItem, ParsedMeal

APP_PATH = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
TEXT_PAGE = "pages/log_text.py"
MANUAL_PAGE = "pages/log_manual.py"


def add_food(session, name, kcal, protein, carbs, fat):
    session.add(
        Food(name=name, source="manual", kcal=kcal, protein_g=protein, carbs_g=carbs, fat_g=fat)
    )


def make_db(tmp_path, monkeypatch, name="test.db", with_foods=True):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = get_engine(url)
    create_db(engine)
    if with_foods:
        with Session(engine) as session:
            add_food(session, "Kwark magere", 51, 8.4, 3.8, 0)
            add_food(session, "Banaan", 90, 1, 20, 0.3)
            session.commit()
    return engine


def button(at, label):
    return next(b for b in at.button if b.label == label)


@pytest.fixture
def engine(tmp_path, monkeypatch):
    engine = make_db(tmp_path, monkeypatch)
    yield engine
    engine.dispose()


@pytest.fixture
def parsed_meal(monkeypatch):
    monkeypatch.setattr(
        "core.parsing.parse_meal",
        lambda text: ParsedMeal(
            items=[
                ParsedItem(name="kwark", quantity=200, unit="g"),
                ParsedItem(name="banaan", quantity=1, unit="piece"),
            ]
        ),
    )


def entries(engine):
    with Session(engine) as session:
        return session.exec(select(FoodEntry).order_by(FoodEntry.id)).all()


# --- Text page ---------------------------------------------------------------


def test_text_page_with_empty_database_shows_import_hint(tmp_path, monkeypatch):
    make_db(tmp_path, monkeypatch, "empty.db", with_foods=False)

    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert "leeg" in at.error[0].value


def test_analyse_then_confirm_saves_entries(engine, parsed_meal):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    at.text_area[0].set_value("200g kwark met een banaan").run()
    button(at, "Analyseer").click().run()

    assert not at.exception
    assert any("geschat" in c.value for c in at.caption)  # banana weight is a guess
    assert at.number_input[0].value == 200
    assert at.number_input[1].value == 100

    at.number_input[1].set_value(120.0).run()
    button(at, "Bevestig en sla op").click().run()

    rows = entries(engine)
    assert [r.amount_g for r in rows] == [200, 120]
    assert rows[0].raw_text == "200g kwark met een banaan"
    assert "opgeslagen" in at.success[0].value


def test_removed_item_is_not_saved(engine, parsed_meal):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    at.text_area[0].set_value("200g kwark met een banaan").run()
    button(at, "Analyseer").click().run()
    at.checkbox[1].check().run()  # remove the banana
    button(at, "Bevestig en sla op").click().run()

    assert len(entries(engine)) == 1


def test_nothing_is_saved_before_confirming(engine, parsed_meal):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    at.text_area[0].set_value("200g kwark met een banaan").run()
    button(at, "Analyseer").click().run()

    assert entries(engine) == []


# --- Manual page -------------------------------------------------------------


def open_manual_page():
    return AppTest.from_file(APP_PATH, default_timeout=30).run().switch_page(MANUAL_PAGE).run()


def test_search_and_add_a_food(engine):
    at = open_manual_page()

    at.text_input(key="manual_query").set_value("banaan").run()
    assert "Banaan" in at.selectbox[0].options[0]

    at.number_input[0].set_value(150.0).run()
    button(at, "Toevoegen").click().run()

    (row,) = entries(engine)
    assert row.amount_g == 150
    assert "opgeslagen" in at.success[0].value


def test_search_without_results_shows_hint(engine):
    at = open_manual_page()

    at.text_input(key="manual_query").set_value("xyzqw").run()

    assert any("Niets gevonden" in i.value for i in at.info)
    assert not [b for b in at.button if b.label == "Toevoegen"]


def fill_new_food(at, name, kcal, protein, carbs, fat):
    at.text_input(key="nf_name").set_value(name)
    at.number_input(key="nf_kcal").set_value(kcal)
    at.number_input(key="nf_protein").set_value(protein)
    at.number_input(key="nf_carbs").set_value(carbs)
    at.number_input(key="nf_fat").set_value(fat)
    return at


def test_create_a_food_then_log_it(engine):
    at = open_manual_page()

    fill_new_food(at, "Eigen granola", 450.0, 10.0, 60.0, 18.0)
    button(at, "Aanmaken").click().run()

    assert "aangemaakt" in at.success[0].value
    with Session(engine) as session:
        food = session.exec(select(Food).where(Food.name == "Eigen granola")).one()
    assert (food.source, food.kcal) == ("manual", 450)

    # The new food is now found by the search box and can be logged.
    assert "Eigen granola" in at.selectbox[0].options[0]
    button(at, "Toevoegen").click().run()
    assert [r.food_id for r in entries(engine)] == [food.id]


def test_invalid_new_food_shows_error_and_creates_nothing(engine):
    at = open_manual_page()

    fill_new_food(at, "Onmogelijk", 500.0, 50.0, 40.0, 20.0)  # 110 g of macros per 100 g
    button(at, "Aanmaken").click().run()

    assert "100 g" in at.error[0].value
    with Session(engine) as session:
        assert session.exec(select(Food).where(Food.name == "Onmogelijk")).first() is None
