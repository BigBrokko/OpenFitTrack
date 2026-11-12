"""Import foods from a CSV file: choose the columns, check a preview, import."""

import re
from pathlib import Path

import streamlit as st
from common import get_app_engine
from sqlmodel import Session

from core.csv_import import ColumnMapping, foods_from_table, guess_mapping, read_csv_table
from core.foods import upsert_foods

engine = get_app_engine()

NO_COLUMN = "—"
MANY_FOODS = 20_000


@st.cache_data
def load_table(data: bytes):
    return read_csv_table(data)


def default_source(file_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", Path(file_name).stem.lower()).strip("-") or "csv"


st.title("Importeren")
st.write(
    "Importeer voedingsmiddelen uit een CSV-bestand, bijvoorbeeld een voedingstabel van je "
    "eigen land. De waarden moeten **per 100 gram** zijn. Importeer je hetzelfde bestand nog "
    "eens, dan worden bestaande regels bijgewerkt en komen er geen dubbelen."
)

if message := st.session_state.pop("import_flash", None):
    st.success(message)

uploaded = st.file_uploader("CSV-bestand", type=["csv", "tsv", "txt"])
if uploaded is None:
    st.stop()

try:
    table = load_table(uploaded.getvalue())
except ValueError as error:
    st.error(str(error))
    st.stop()

frame = table.frame
st.caption(f"{len(frame)} regels · scheidingsteken `{table.delimiter}` · tekenset {table.encoding}")
st.dataframe(frame.head(5), hide_index=True, width="stretch")

st.subheader("Welke kolom is wat?")
columns = list(frame.columns)
guess = guess_mapping(columns)
file_key = uploaded.file_id  # a new file resets the choices


def pick(label: str, field: str) -> str | None:
    options = [NO_COLUMN, *columns]
    default = options.index(guess[field]) if guess[field] in options else 0
    choice = st.selectbox(label, options, index=default, key=f"map_{field}_{file_key}")
    return None if choice == NO_COLUMN else choice


col_left, col_right = st.columns(2)
with col_left:
    name = pick("Naam *", "name")
    protein = pick("Eiwit (g) *", "protein_g")
    carbs = pick("Koolhydraten (g) *", "carbs_g")
    fat = pick("Vet (g) *", "fat_g")
with col_right:
    kcal = pick("kcal", "kcal")
    kj = pick("kJ (alleen gebruikt als kcal leeg is)", "kj")
    source_id = pick("ID (optioneel, om later bij te werken)", "source_id")
    source = st.text_input(
        "Naam van deze bron", value=default_source(uploaded.name), key=f"source_{file_key}"
    )

if not (name and protein and carbs and fat and (kcal or kj)):
    st.info("Kies minstens de kolommen voor naam, eiwit, koolhydraten, vet en kcal (of kJ).")
    st.stop()

mapping = ColumnMapping(
    name=name, protein_g=protein, carbs_g=carbs, fat_g=fat, kcal=kcal, kj=kj, source_id=source_id
)
try:
    parsed = foods_from_table(frame, mapping, source)
except ValueError as error:
    st.error(str(error))
    st.stop()

st.subheader("Controle")
col_ok, col_skipped = st.columns(2)
col_ok.metric("Bruikbare regels", len(parsed.foods))
col_skipped.metric("Overgeslagen", len(parsed.skipped))

if parsed.foods:
    st.dataframe(
        [
            {
                "Naam": f.name,
                "kcal": round(f.kcal),
                "Eiwit (g)": f.protein_g,
                "Koolhydraten (g)": f.carbs_g,
                "Vet (g)": f.fat_g,
            }
            for f in parsed.foods[:5]
        ],
        hide_index=True,
        width="stretch",
    )
if parsed.skipped:
    with st.expander(f"Waarom zijn {len(parsed.skipped)} regels overgeslagen?"):
        st.dataframe(
            [{"Regel": s.row, "Reden": s.reason} for s in parsed.skipped[:10]],
            hide_index=True,
            width="stretch",
        )
        if len(parsed.skipped) > 10:
            st.caption(f"En nog {len(parsed.skipped) - 10} andere regels.")
if len(parsed.foods) > MANY_FOODS:
    st.warning(
        f"Dit zijn {len(parsed.foods)} voedingsmiddelen. Zoeken wordt daardoor merkbaar "
        "trager. Filter het bestand eerst als dat een probleem wordt."
    )

confirmed = st.checkbox("De waarden in dit bestand zijn per 100 gram", key=f"confirm_{file_key}")
if st.button("Importeren", type="primary", disabled=not (confirmed and parsed.foods)):
    with Session(engine) as session:
        result = upsert_foods(session, parsed.foods, source.strip())
    st.session_state.import_flash = (
        f"Bron '{source.strip()}': {result.added} toegevoegd, {result.updated} bijgewerkt, "
        f"{len(parsed.skipped)} overgeslagen."
    )
    st.rerun()
