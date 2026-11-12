"""Streamlit smoke tests for both logging pages, run against a temporary database."""

from pathlib import Path

import pytest
from sqlmodel import Session, select
from streamlit.testing.v1 import AppTest

from core.db import create_db, get_engine
from core.models import Food, FoodEntry, Goal, WeightEntry
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


# --- Goals page --------------------------------------------------------------


def open_goals_page():
    return AppTest.from_file(APP_PATH, default_timeout=30).run().switch_page("pages/goals.py").run()


def goals(engine):
    with Session(engine) as session:
        return session.exec(select(Goal).order_by(Goal.valid_from)).all()


def test_goals_page_without_goal_shows_hint(engine):
    at = open_goals_page()

    assert not at.exception
    assert "nog geen doel" in at.info[0].value


def test_save_a_goal(engine):
    at = open_goals_page()

    at.number_input[0].set_value(2200.0)
    at.number_input[1].set_value(160.0)
    at.number_input[2].set_value(240.0)
    at.number_input[3].set_value(65.0)
    button(at, "Opslaan").click().run()

    (goal,) = goals(engine)
    assert (goal.kcal, goal.protein_g, goal.carbs_g, goal.fat_g) == (2200, 160, 240, 65)
    assert goal.target_weight_kg is None
    assert "opgeslagen" in at.success[0].value
    assert "2200 kcal" in at.info[0].value


def test_save_goal_with_target_weight(engine):
    at = open_goals_page()

    at.checkbox[0].check()
    at.number_input[4].set_value(75.0)
    button(at, "Opslaan").click().run()

    assert goals(engine)[0].target_weight_kg == 75


def test_invalid_goal_shows_error(engine):
    at = open_goals_page()

    at.number_input[0].set_value(0.0)
    button(at, "Opslaan").click().run()

    assert "kcal" in at.error[0].value
    assert goals(engine) == []


# --- Day page ----------------------------------------------------------------


def open_day_page():
    return AppTest.from_file(APP_PATH, default_timeout=30).run().switch_page("pages/day.py").run()


def log_today(engine, grams):
    from datetime import datetime

    with Session(engine) as session:
        food = session.exec(select(Food).where(Food.name == "Kwark magere")).one()
        session.add(FoodEntry(food_id=food.id, logged_at=datetime.now(), amount_g=grams))
        session.commit()


def add_goal(engine, kcal):
    from datetime import date

    with Session(engine) as session:
        session.add(
            Goal(valid_from=date(2020, 1, 1), kcal=kcal, protein_g=100, carbs_g=200, fat_g=50)
        )
        session.commit()


def test_day_page_without_entries_or_goal(engine):
    at = open_day_page()

    assert not at.exception
    infos = " ".join(i.value for i in at.info)
    assert "geen doel" in infos
    assert "niets gelogd" in infos


def test_day_page_shows_entries_against_goal(engine):
    add_goal(engine, 2000)
    log_today(engine, 200)  # 200 g of 51 kcal / 100 g = 102 kcal
    at = open_day_page()

    assert not at.exception
    assert at.metric[0].value == "102 kcal"
    assert any("van 2000 · nog 1898 kcal" in c.value for c in at.caption)
    assert "Kwark magere" in str(at.dataframe[0].value)


def test_day_page_shows_overage(engine):
    add_goal(engine, 50)
    log_today(engine, 200)
    at = open_day_page()

    assert any("+52 kcal over" in c.value for c in at.caption)


# --- Weight page -------------------------------------------------------------


def open_weight_page():
    return (
        AppTest.from_file(APP_PATH, default_timeout=30).run().switch_page("pages/weight.py").run()
    )


def weights(engine):
    with Session(engine) as session:
        return session.exec(select(WeightEntry).order_by(WeightEntry.date)).all()


def test_weight_page_without_data_shows_hint(engine):
    at = open_weight_page()

    assert not at.exception
    assert "Nog geen gewicht" in at.info[0].value


def test_log_a_weight_shows_trend(engine):
    at = open_weight_page()

    at.number_input[0].set_value(80.5)
    button(at, "Opslaan").click().run()

    (row,) = weights(engine)
    assert row.weight_kg == 80.5
    assert "opgeslagen" in at.success[0].value
    assert at.metric[0].value == "80.5 kg"
    assert at.metric[2].value == "—"  # a single measurement has no weekly change yet


def test_logging_the_same_day_twice_replaces_it(engine):
    at = open_weight_page()

    at.number_input[0].set_value(80.5)
    button(at, "Opslaan").click().run()
    at.number_input[0].set_value(79.9)
    button(at, "Opslaan").click().run()

    assert [w.weight_kg for w in weights(engine)] == [79.9]


def test_implausible_weight_shows_error(engine):
    at = open_weight_page()

    at.number_input[0].set_value(750.0)
    button(at, "Opslaan").click().run()

    assert "between" in at.error[0].value
    assert weights(engine) == []


# --- Import and edit pages ---------------------------------------------------


def test_import_page_asks_for_a_file(engine):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run().switch_page("pages/import_foods.py")
    at.run()

    assert not at.exception
    assert at.title[0].value == "Importeren"


def own_food(engine, name="Eigen granola", kcal=450.0):
    with Session(engine) as session:
        food = Food(name=name, source="manual", kcal=kcal, protein_g=10, carbs_g=60, fat_g=18)
        session.add(food)
        session.commit()
        return food.id


def test_edit_an_own_food(engine):
    food_id = own_food(engine)
    at = open_manual_page()

    at.selectbox(key="edit_pick").set_value(food_id).run()
    at.number_input(key=f"ef_kcal_{food_id}").set_value(400.0)
    button(at, "Opslaan").click().run()

    with Session(engine) as session:
        assert session.get(Food, food_id).kcal == 400
    assert "bijgewerkt" in at.success[0].value


def test_edit_shows_validation_errors_and_changes_nothing(engine):
    food_id = own_food(engine)
    at = open_manual_page()

    at.selectbox(key="edit_pick").set_value(food_id).run()
    at.number_input(key=f"ef_p_{food_id}").set_value(80.0)  # 80 + 60 + 18 g per 100 g
    button(at, "Opslaan").click().run()

    assert "100 g" in at.error[0].value
    with Session(engine) as session:
        assert session.get(Food, food_id).protein_g == 10


def test_edit_section_without_own_foods_says_so(tmp_path, monkeypatch):
    make_db(tmp_path, monkeypatch, "nofoods.db", with_foods=False)
    at = open_manual_page()

    assert any("nog geen eigen" in c.value for c in at.caption)
