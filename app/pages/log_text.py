"""Log food in plain language, with a confirmation step before anything is saved."""

import streamlit as st
from common import format_nutrients, get_app_engine, pick_datetime
from sqlmodel import Session, func, select

from core.meal_log import propose_entries, save_entries
from core.models import Food
from core.nutrition import Nutrients, entry_nutrients
from core.parsing import ParseError, parse_meal

engine = get_app_engine()

st.title("Eten loggen")

with Session(engine) as session:
    food_count = session.exec(select(func.count()).select_from(Food)).one()
if food_count == 0:
    st.error(
        "De voedingsdatabase is leeg. Importeer eerst NEVO met "
        "`uv run python scripts/import_nevo.py <pad naar NEVO csv>`, "
        "of maak zelf voedingsmiddelen aan bij 'Handmatig toevoegen'."
    )
    st.stop()

st.session_state.setdefault("proposals", None)
st.session_state.setdefault("raw_text", "")
st.session_state.setdefault("analysis_id", 0)

if message := st.session_state.pop("flash", None):
    st.success(message)

text = st.text_area("Wat heb je gegeten?", placeholder="200g kwark met een banaan")
logged_at = pick_datetime()

if st.button("Analyseer", type="primary", disabled=not text.strip()):
    try:
        with st.spinner("Bezig met analyseren..."):
            meal = parse_meal(text)
        with Session(engine) as session:
            st.session_state.proposals = propose_entries(session, meal)
        st.session_state.raw_text = text
        st.session_state.analysis_id += 1
    except ParseError as error:
        st.session_state.proposals = None
        st.error(str(error))

proposals = st.session_state.proposals
if proposals is None:
    st.stop()
if not proposals:
    st.info("Ik vond geen eten in je tekst. Probeer het anders te formuleren.")
    st.stop()

st.subheader("Controleer en bevestig")
chosen: list[tuple[Food, float]] = []
total = Nutrients.zero()

for i, proposal in enumerate(proposals):
    key = f"{st.session_state.analysis_id}_{i}"
    item = proposal.item
    with st.container(border=True):
        st.markdown(f"**{item.name}** — {item.quantity:g} {item.unit}")
        if not proposal.candidates:
            st.warning("Niet gevonden in de database. Dit item wordt niet opgeslagen.")
            continue

        col_food, col_grams, col_remove = st.columns([3, 1.5, 1])
        index = col_food.selectbox(
            "Voedingsmiddel",
            range(len(proposal.candidates)),
            format_func=lambda j, candidates=proposal.candidates: candidates[j].food.name,
            key=f"food_{key}",
            label_visibility="collapsed",
        )
        grams = col_grams.number_input(
            "Gram",
            min_value=0.0,
            value=round(proposal.amount_g, 1),
            step=5.0,
            key=f"grams_{key}",
            label_visibility="collapsed",
        )
        remove = col_remove.checkbox("Verwijder", key=f"remove_{key}")

        food = proposal.candidates[index].food
        nutrients = entry_nutrients(food, grams)
        st.caption(format_nutrients(nutrients))
        if proposal.estimated:
            st.caption("⚠ Hoeveelheid geschat — controleer het aantal gram.")

        if not remove and grams > 0:
            chosen.append((food, grams))
            total += nutrients

st.markdown(f"**Totaal:** {format_nutrients(total)}")

if st.button("Bevestig en sla op", type="primary", disabled=not chosen):
    with Session(engine) as session:
        save_entries(session, chosen, logged_at=logged_at, raw_text=st.session_state.raw_text)
    st.session_state.proposals = None
    st.session_state.flash = f"{len(chosen)} item(s) opgeslagen ({total.kcal:.0f} kcal)."
    st.rerun()
