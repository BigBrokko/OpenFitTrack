"""Entry point and navigation. Run with: uv run streamlit run app/main.py"""

import sys
from pathlib import Path

# Allow `streamlit run app/main.py` from the repo root to find the `core` package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
st.set_page_config(page_title="OpenFitTrack", page_icon="🥗")

navigation = st.navigation(
    [
        st.Page("pages/log_manual.py", title="Eten loggen", icon="🍽️", default=True),
        st.Page("pages/import_foods.py", title="Importeren", icon="📥"),
        st.Page("pages/day.py", title="Dagoverzicht", icon="📅"),
        st.Page("pages/weight.py", title="Gewicht", icon="⚖️"),
        st.Page("pages/goals.py", title="Doelen", icon="🎯"),
    ]
)
navigation.run()
