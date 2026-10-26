"""Home page: one card per business and the dialog to create a new dashboard (decision D-022)."""

import json
import subprocess
import sys
from datetime import date

import pandas as pd
import streamlit as st

from common import apify_token, cost_notice, decimal, markdown_safe, percent, reload, remember_token, thousands
from impacto import analysis, database
from impacto.pipeline import collect


def find_place(query: str) -> dict:
    """Free Google Maps search, run as a separate process (Playwright and Streamlit do not mix)."""
    result = subprocess.run([sys.executable, "-m", "impacto.sources.google_maps", query],
                            capture_output=True, text=True, encoding="utf-8", timeout=120)
    lines = result.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else {"error": result.stderr[-500:]}


@st.dialog("Crear dashboard nuevo", width="large")
def create_dashboard() -> None:
    st.markdown("Busca un negocio en Google Maps, elige cuántas reseñas descargar y se clasificarán con el modelo.")
    # A form sends the text with the button or Enter; a plain text box only does so when it loses focus
    with st.form("search", border=False):
        query = st.text_input("Negocio", placeholder="Nombre y ciudad, p. ej. «El Corte Inglés Princesa Madrid»")
        searched = st.form_submit_button("Buscar", icon=":material/search:")
    if searched and query.strip():
        with st.spinner("Buscando en Google Maps…"):
            st.session_state["place_search"] = find_place(query.strip())

    search = st.session_state.get("place_search")
    if search is None:
        return
    if "error" in search or not (search.get("place") or search.get("candidates")):
        st.warning("No se ha encontrado ningún negocio con ese nombre. Prueba a añadir la ciudad o la dirección.")
        return

    if search.get("place"):
        place = search["place"]
    else:
        options = search["candidates"]
        index = st.radio("Hay varios resultados: elige uno", range(len(options)),
                         format_func=lambda i: " · ".join(str(value) for value in (
                             options[i]["name"], options[i].get("address"),
                             f"{decimal(options[i]['rating'], 1)}★" if options[i].get("rating") else None) if value))
        place = options[index]
    st.markdown(f"**{place['name']}**  \n{place.get('address') or ''}"
                + (f" · {decimal(place['rating'], 1)}★ en Google" if place.get("rating") else ""))

    st.divider()
    reviews = st.number_input("Reseñas a descargar (las más recientes)", min_value=10, value=200, step=50,
                              help="El número total de reseñas del negocio se conoce al descargar.")
    since = None
    if st.checkbox("Solo reseñas desde una fecha"):
        since = st.date_input("Desde", value=date(2019, 1, 1), format="DD/MM/YYYY").isoformat()
    token = apify_token("create")
    cost_notice(token, reviews)

    if st.button("Crear dashboard", type="primary", icon=":material/add_chart:", disabled=not token):
        remember_token("create")
        with st.status("Descargando y clasificando reseñas…", expanded=True) as status:
            try:
                summary = collect(database.connect(), reviews, place_url=place["url"], since=since, token=token,
                                  on_progress=lambda message: status.write(markdown_safe(message)))
            except Exception as error:
                status.update(label="No se ha podido completar la descarga", state="error")
                st.error(str(error))
                return
            if not summary["reviews"]:
                status.update(label="Apify no ha devuelto reseñas", state="error")
                st.error("Puede que el negocio no tenga reseñas en ese periodo o que se haya agotado el crédito.")
                return
            status.update(label="Dashboard creado", state="complete")
        st.session_state.pop("place_search", None)
        reload()
        st.query_params["place"] = summary["place_id"]
        st.rerun()


def card(place: pd.Series, reviews: pd.DataFrame) -> None:
    headline = analysis.last_months(reviews)["current"]
    with st.container(border=True):
        st.markdown(f"#### {place['name']}")
        st.caption(place["address"] or "")
        first, second = st.columns(2)
        first.metric("Nota en Google", f"{decimal(place['rating'], 1)}★" if pd.notna(place["rating"]) else "—")
        second.metric("Reseñas analizadas", thousands(len(reviews)))
        first.metric("Malas según el modelo", percent(headline["bad_share"]), help="Últimos 12 meses, texto en español.")
        second.metric("Con 1–2★", percent(headline["low_stars_share"]), help="Últimos 12 meses, todas las reseñas.")
        st.caption(f"Del {reviews['published_at'].min():%d/%m/%Y} al {reviews['published_at'].max():%d/%m/%Y}")
        if st.button("Abrir dashboard", key=f"open_{place['place_id']}", icon=":material/dashboard:", width="stretch"):
            st.query_params["place"] = place["place_id"]
            st.rerun()


def render(reviews: pd.DataFrame, places: pd.DataFrame) -> None:
    st.title("impacto: qué opinan los clientes")
    st.caption("Reseñas de Google clasificadas como buenas o malas por un modelo de texto entrenado en Neural Designer "
               "y ejecutado con OpenNN.")
    if st.button("Crear dashboard nuevo", type="primary", icon=":material/add:"):
        st.session_state.pop("place_search", None)
        create_dashboard()

    if places.empty:
        st.info("Todavía no hay ningún negocio. Pulsa «Crear dashboard nuevo» para empezar.")
        return
    columns = st.columns(3)
    for index, place in enumerate(places.itertuples(index=False)):
        place = pd.Series(place._asdict())
        place_reviews = reviews[reviews["place_id"] == place["place_id"]]
        if not place_reviews.empty:
            with columns[index % 3]:
                card(place, place_reviews)
