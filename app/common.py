"""Helpers shared by the app pages."""

import os
from datetime import date, datetime

import streamlit as st
from sqlalchemy.engine import Engine

from core.db import DEFAULT_DATABASE_URL, create_db, get_engine
from core.nutrition import Nutrients


@st.cache_resource
def _engine_for(url: str) -> Engine:
    engine = get_engine(url)
    create_db(engine)
    return engine


def get_app_engine() -> Engine:
    return _engine_for(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def format_nutrients(n: Nutrients) -> str:
    return (
        f"{n.kcal:.0f} kcal · {n.protein_g:.1f} g eiwit · "
        f"{n.carbs_g:.1f} g kh · {n.fat_g:.1f} g vet"
    )


def pick_datetime() -> datetime:
    """Date and time inputs (default: now), shared between pages via session state."""
    st.session_state.setdefault("log_day", date.today())
    st.session_state.setdefault("log_time", datetime.now().time().replace(second=0, microsecond=0))
    col_date, col_time = st.columns(2)
    day = col_date.date_input("Datum", key="log_day")
    at = col_time.time_input("Tijd", key="log_time")
    return datetime.combine(day, at)
