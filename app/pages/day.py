"""Overview of one day: what was eaten, compared to the goal that applied on that day."""

from datetime import date

import streamlit as st
from common import format_nutrients, get_app_engine
from sqlmodel import Session

from core.day_summary import compare_to_goal, day_entries
from core.db import get_current_goal
from core.nutrition import Nutrients

engine = get_app_engine()

st.title("Dagoverzicht")

day = st.date_input("Dag", value=date.today())

with Session(engine) as session:
    entries = day_entries(session, day)
    goal = get_current_goal(session, day)

totals = Nutrients.zero()
for entry in entries:
    totals += entry.nutrients

if goal is None:
    st.info("Voor deze dag is geen doel. Stel er een in bij 'Doelen'.")
    st.markdown(f"**Totaal:** {format_nutrients(totals)}")
else:
    progress = compare_to_goal(totals, goal)
    labels = {
        "kcal": ("kcal", "kcal"),
        "protein_g": ("Eiwit", "g"),
        "carbs_g": ("Koolhydraten", "g"),
        "fat_g": ("Vet", "g"),
    }
    for column, (key, (label, unit)) in zip(st.columns(4), labels.items(), strict=True):
        p = progress[key]
        with column:
            st.metric(label, f"{p.eaten:.0f} {unit}")
            st.progress(min(p.percent / 100, 1.0))
            if p.remaining >= 0:
                st.caption(f"van {p.goal:.0f} · nog {p.remaining:.0f} {unit}")
            else:
                st.caption(f"van {p.goal:.0f} · +{-p.remaining:.0f} {unit} over")
    st.caption(f"Doel geldig vanaf {goal.valid_from:%d-%m-%Y}.")

st.subheader("Gegeten")
if not entries:
    st.info("Voor deze dag is niets gelogd.")
else:
    st.dataframe(
        [
            {
                "Tijd": f"{e.logged_at:%H:%M}",
                "Voedingsmiddel": e.food_name,
                "Gram": e.amount_g,
                "kcal": round(e.nutrients.kcal),
                "Eiwit (g)": round(e.nutrients.protein_g, 1),
                "Koolhydraten (g)": round(e.nutrients.carbs_g, 1),
                "Vet (g)": round(e.nutrients.fat_g, 1),
            }
            for e in entries
        ],
        hide_index=True,
        width="stretch",
    )
