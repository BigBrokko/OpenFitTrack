"""Log your weight and see it with an EMA trend line."""

from datetime import date

import plotly.graph_objects as go
import streamlit as st
from common import get_app_engine
from sqlmodel import Session

from core.db import get_current_goal
from core.weight import list_weights, log_weight, trend_change, weight_trend

engine = get_app_engine()

st.title("Gewicht")

if message := st.session_state.pop("weight_flash", None):
    st.success(message)

with Session(engine) as session:
    weights = list_weights(session)
    goal = get_current_goal(session, date.today())

last_weight = weights[-1].weight_kg if weights else 75.0
with st.form("weight_form"):
    col_day, col_kg = st.columns(2)
    day = col_day.date_input("Datum", value=date.today())
    weight_kg = col_kg.number_input("Gewicht (kg)", min_value=0.0, step=0.1, value=last_weight)
    submitted = st.form_submit_button("Opslaan", type="primary")

if submitted:
    try:
        with Session(engine) as session:
            log_weight(session, day, weight_kg)
    except ValueError as error:
        st.error(str(error))
    else:
        st.session_state.weight_flash = f"{weight_kg:g} kg opgeslagen voor {day:%d-%m-%Y}."
        st.rerun()

if not weights:
    st.info("Nog geen gewicht gelogd.")
    st.stop()

trend = weight_trend(weights)
latest = trend.iloc[-1]
change = trend_change(trend)

col_latest, col_trend, col_change = st.columns(3)
col_latest.metric("Laatste meting", f"{latest.weight_kg:.1f} kg")
col_trend.metric("Trend", f"{latest.trend_kg:.1f} kg")
col_change.metric(
    "Trend over 7 dagen",
    "—" if change is None else f"{change:+.1f} kg",
)

figure = go.Figure()
figure.add_scatter(x=trend["date"], y=trend["weight_kg"], mode="markers", name="Gewicht")
figure.add_scatter(x=trend["date"], y=trend["trend_kg"], mode="lines", name="Trend (EMA)")
if goal and goal.target_weight_kg:
    figure.add_hline(
        y=goal.target_weight_kg,
        line_dash="dash",
        annotation_text=f"Streefgewicht {goal.target_weight_kg:g} kg",
    )
if goal and goal.target_weight_kg:
    # A line does not widen the axis by itself, so include the target in the visible range.
    values = [*trend["weight_kg"], *trend["trend_kg"], goal.target_weight_kg]
    figure.update_yaxes(range=[min(values) - 0.5, max(values) + 0.5])
figure.update_layout(
    yaxis_title="kg",
    margin={"l": 0, "r": 0, "t": 10, "b": 0},
    legend={"orientation": "h", "y": -0.2},
)
st.plotly_chart(figure, width="stretch")
