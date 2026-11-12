"""Log food: search the database, enter an amount, or create a missing food yourself."""

import streamlit as st
from common import format_nutrients, get_app_engine, pick_datetime
from sqlmodel import Session, func, select

from core.foods import add_manual_food, list_manual_foods, update_manual_food
from core.matching import search_foods
from core.meal_log import save_entries
from core.models import Food
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


st.title("Eten loggen")

if message := st.session_state.pop("flash", None):
    st.success(message)

with Session(engine) as session:
    food_count = session.exec(select(func.count()).select_from(Food)).one()
if food_count == 0:
    st.info(
        "De voedingsdatabase is leeg. Importeer voedingsmiddelen uit een CSV-bestand bij "
        "'Importeren', of maak hieronder je eerste voedingsmiddel aan."
    )

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
            save_entries(session, [(food, grams)], logged_at=logged_at)
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

edit_message = st.session_state.pop("edit_message", None)
with st.expander("Eigen producten bewerken", expanded=edit_message is not None):
    if edit_message:
        st.success(edit_message)

    with Session(engine) as session:
        own_foods = list_manual_foods(session)
    if not own_foods:
        st.caption("Je hebt nog geen eigen voedingsmiddelen.")
    else:
        st.caption(
            "Alleen producten die je zelf hebt aangemaakt. Al gelogde regels gebruiken "
            "meteen de nieuwe waarden."
        )
        names = {f.id: f.name for f in own_foods}
        food_id = st.selectbox("Product", list(names), format_func=names.get, key="edit_pick")
        current = next(f for f in own_foods if f.id == food_id)

        with st.form("edit_food"):
            new_name = st.text_input("Naam", value=current.name, key=f"ef_name_{food_id}")
            st.caption("Waarden per 100 g")
            col_kcal, col_protein, col_carbs, col_fat = st.columns(4)
            new_kcal = col_kcal.number_input(
                "kcal", min_value=0.0, step=1.0, value=current.kcal, key=f"ef_kcal_{food_id}"
            )
            new_protein = col_protein.number_input(
                "Eiwit (g)", min_value=0.0, step=0.1, value=current.protein_g, key=f"ef_p_{food_id}"
            )
            new_carbs = col_carbs.number_input(
                "Koolhydraten (g)",
                min_value=0.0,
                step=0.1,
                value=current.carbs_g,
                key=f"ef_c_{food_id}",
            )
            new_fat = col_fat.number_input(
                "Vet (g)", min_value=0.0, step=0.1, value=current.fat_g, key=f"ef_f_{food_id}"
            )
            submitted = st.form_submit_button("Opslaan")

        if submitted:
            try:
                with Session(engine) as session:
                    update_manual_food(
                        session, food_id, new_name, new_kcal, new_protein, new_carbs, new_fat
                    )
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.edit_message = f"'{new_name.strip()}' is bijgewerkt."
                st.rerun()
