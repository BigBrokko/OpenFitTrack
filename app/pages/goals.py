"""Set daily goals. Each save is a new goal valid from a date; history is kept."""

from datetime import date

import streamlit as st
from common import get_app_engine
from sqlmodel import Session

from core.db import get_current_goal
from core.goals import list_goals, set_goal

engine = get_app_engine()

st.title("Doelen")

if message := st.session_state.pop("goal_flash", None):
    st.success(message)

with Session(engine) as session:
    current = get_current_goal(session, date.today())
    goals = list_goals(session)

if current:
    target = f" · streefgewicht {current.target_weight_kg:g} kg" if current.target_weight_kg else ""
    st.info(
        f"Huidig doel (sinds {current.valid_from:%d-%m-%Y}): {current.kcal:.0f} kcal · "
        f"{current.protein_g:g} g eiwit · {current.carbs_g:g} g kh · "
        f"{current.fat_g:g} g vet{target}"
    )
else:
    st.info("Je hebt nog geen doel ingesteld.")

defaults = current
with st.form("goal_form"):
    valid_from = st.date_input("Geldig vanaf", value=date.today())
    kcal = st.number_input(
        "kcal per dag", min_value=0.0, step=50.0, value=defaults.kcal if defaults else 2000.0
    )
    col_p, col_c, col_f = st.columns(3)
    protein = col_p.number_input(
        "Eiwit (g)", min_value=0.0, step=5.0, value=defaults.protein_g if defaults else 0.0
    )
    carbs = col_c.number_input(
        "Koolhydraten (g)", min_value=0.0, step=5.0, value=defaults.carbs_g if defaults else 0.0
    )
    fat = col_f.number_input(
        "Vet (g)", min_value=0.0, step=5.0, value=defaults.fat_g if defaults else 0.0
    )
    use_target = st.checkbox(
        "Streefgewicht instellen", value=bool(defaults and defaults.target_weight_kg)
    )
    target_weight = st.number_input(
        "Streefgewicht (kg)",
        min_value=0.0,
        step=0.5,
        value=(defaults.target_weight_kg if defaults and defaults.target_weight_kg else 70.0),
    )
    submitted = st.form_submit_button("Opslaan", type="primary")

macro_kcal = 4 * protein + 4 * carbs + 9 * fat
st.caption(
    f"Je macro's samen zijn {macro_kcal:.0f} kcal (4 per g eiwit en kh, 9 per g vet), "
    f"je kcal-doel is {kcal:.0f}."
)

if submitted:
    try:
        with Session(engine) as session:
            set_goal(
                session,
                valid_from,
                kcal,
                protein,
                carbs,
                fat,
                target_weight_kg=target_weight if use_target else None,
            )
    except ValueError as error:
        st.error(str(error))
    else:
        st.session_state.goal_flash = f"Doel opgeslagen (geldig vanaf {valid_from:%d-%m-%Y})."
        st.rerun()

if goals:
    st.subheader("Geschiedenis")
    st.dataframe(
        [
            {
                "Vanaf": g.valid_from,
                "kcal": g.kcal,
                "Eiwit (g)": g.protein_g,
                "Koolhydraten (g)": g.carbs_g,
                "Vet (g)": g.fat_g,
                "Streefgewicht (kg)": g.target_weight_kg,
            }
            for g in goals
        ],
        hide_index=True,
        width="stretch",
    )
