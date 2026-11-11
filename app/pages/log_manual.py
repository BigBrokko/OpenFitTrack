"""Search for a food by hand (no AI), log it, or create a missing food yourself."""

import streamlit as st
from common import format_nutrients, get_app_engine, pick_datetime
from sqlmodel import Session

from core.foods import add_manual_food
from core.matching import search_foods
from core.meal_log import save_entries
from core.nutrition import entry_nutrients

engine = get_app_engine()


def create_food() -> None:
    """Form callback: runs before the rerun, so it may set the search box value."""
    state = st.session_state
    try:
        with Session(engine) as session:
            food = add_manual_food(
                session,
                state.nf_name,
                state.nf_kcal,
                state.nf_protein,
                state.nf_carbs,
                state.nf_fat,
            )
            name = food.name
    except ValueError as error:
        state.food_message = ("error", str(error))
        return
    state.manual_query = name
    state.food_message = ("success", f"'{name}' is aangemaakt. Je vindt het bij de resultaten.")


st.title("Handmatig toevoegen")

if message := st.session_state.pop("flash", None):
    st.success(message)

query = st.text_input("Zoek een voedingsmiddel", key="manual_query")
results = []
if query.strip():
    with Session(engine) as session:
        results = search_foods(session, query, limit=10)
    if not results:
        st.info("Niets gevonden. Maak hieronder zelf een voedingsmiddel aan.")

if results:
    index = st.selectbox(
        "Resultaat",
        range(len(results)),
        format_func=lambda j: f"{results[j].food.name} — {results[j].food.kcal:.0f} kcal / 100 g",
    )
    food = results[index].food
    grams = st.number_input("Hoeveelheid (gram)", min_value=0.0, value=100.0, step=5.0)
    st.caption(format_nutrients(entry_nutrients(food, grams)))
    logged_at = pick_datetime()

    if st.button("Toevoegen", type="primary", disabled=grams <= 0):
        with Session(engine) as session:
            save_entries(session, [(food, grams)], logged_at=logged_at, raw_text=None)
        st.session_state.flash = f"{food.name} ({grams:g} g) opgeslagen."
        st.rerun()

with st.expander("Niet gevonden? Maak zelf een voedingsmiddel aan"):
    if food_message := st.session_state.pop("food_message", None):
        kind, text = food_message
        (st.error if kind == "error" else st.success)(text)

    with st.form("new_food"):
        st.text_input("Naam", key="nf_name")
        st.caption("Waarden per 100 g")
        col_kcal, col_protein, col_carbs, col_fat = st.columns(4)
        col_kcal.number_input("kcal", min_value=0.0, step=1.0, key="nf_kcal")
        col_protein.number_input("Eiwit (g)", min_value=0.0, step=0.1, key="nf_protein")
        col_carbs.number_input("Koolhydraten (g)", min_value=0.0, step=0.1, key="nf_carbs")
        col_fat.number_input("Vet (g)", min_value=0.0, step=0.1, key="nf_fat")
        st.form_submit_button("Aanmaken", on_click=create_food)
