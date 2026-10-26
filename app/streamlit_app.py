"""impacto: what customers think of a business (decisions D-020, D-022).

Run from the repository root:
    uv run streamlit run app/streamlit_app.py

The home page shows one card per business and a button to create a new dashboard; each card opens the
dashboard of that business (?place=<Google place id>). The database is SQLite by default, or the one in
DATABASE_URL (PostgreSQL in Docker).
"""

import streamlit as st

import dashboard
import home
from common import SOURCE_CODE, load
from impacto import database

st.set_page_config(page_title="impacto · Qué opinan los clientes", layout="wide")

reviews, places = load(database.database_url())
place_id = st.query_params.get("place")
selected = places[places["place_id"] == place_id]

if place_id and not selected.empty:
    dashboard.render(selected.iloc[0], reviews[reviews["place_id"] == place_id])
else:
    home.render(reviews, places)

st.divider()
st.caption(
    "Análisis educativo de reseñas públicas, sin relación con los negocios analizados. Reseñas recogidas de Google "
    "Maps con Apify, sin datos de sus autores. Modelo de clasificación de texto entrenado en Neural Designer y "
    f"ejecutado con OpenNN. Código fuente (AGPL-3.0): [{SOURCE_CODE}]({SOURCE_CODE})")
