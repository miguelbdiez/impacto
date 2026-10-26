"""Shared pieces of the app: colours, number formats, data loading and the Apify controls."""

import altair as alt
import pandas as pd
import streamlit as st

from impacto import analysis, database
from impacto.sources.apify import ApifyReviews, estimated_cost_usd, find_token, save_token

SOURCE_CODE = "https://github.com/miguelbdiez/impacto"
APIFY_TOKENS_PAGE = "https://console.apify.com/settings/integrations"

# Validated reference palette (dataviz skill): categorical slots 1-2 for the two measures, the
# blue <-> red diverging pair for good/bad, gray for context. Dark mode uses its own steps.
PALETTES = {
    "light": {"model": "#2a78d6", "stars": "#eb6834", "good": "#2a78d6", "bad": "#e34948",
              "context": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "text": "#52514e",
              "surface": "#ffffff"},
    "dark": {"model": "#3987e5", "stars": "#d95926", "good": "#3987e5", "bad": "#e66767",
             "context": "#898781", "grid": "#2c2c2a", "axis": "#383835", "text": "#c3c2b7",
             "surface": "#0e1117"},
}


def colors() -> dict:
    # A theme fixed in the configuration wins; otherwise st.context reports the viewer's (browser or menu)
    # choice. st.context alone is not enough: with a configured theme it still reports the browser preference.
    theme = st.get_option("theme.base") or getattr(getattr(st.context, "theme", None), "type", None) or "light"
    return PALETTES["dark" if theme == "dark" else "light"]


def chart_config(chart: alt.Chart) -> alt.Chart:
    """Hairline, solid, recessive axes and grid; text in ink colours, never in series colours."""
    palette = colors()
    return (chart.configure_axis(gridColor=palette["grid"], domainColor=palette["axis"], tickColor=palette["axis"],
                                 labelColor=palette["text"], titleColor=palette["text"], gridWidth=1,
                                 labelFontWeight="normal", titleFontWeight="normal")
                 .configure_legend(labelColor=palette["text"], titleColor=palette["text"], orient="top",
                                   title=None, symbolStrokeWidth=2, labelLimit=0)
                 .configure_view(strokeWidth=0))


def percent(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.0%}"


def thousands(number: int) -> str:
    """Spanish thousands separator: 7490 -> 7.490."""
    return f"{number:,}".replace(",", ".")


def decimal(value: float, digits: int = 2) -> str:
    """Spanish decimal comma: 4.1 -> 4,10."""
    return f"{value:.{digits}f}".replace(".", ",")


@st.cache_data(show_spinner=False)
def load(url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every review (with its prediction) and every place in the database."""
    with database.connect(url).connect() as connection:
        return analysis.load_reviews(connection, database.MODEL), analysis.load_places(connection)


def reload() -> None:
    load.clear()
    apify_credit.clear()


@st.cache_data(ttl=60, show_spinner=False)
def apify_credit(token: str) -> dict | None:
    try:
        return ApifyReviews(token).credit()
    except Exception:  # wrong token or no connection: the dialog says so
        return None


def apify_token(key: str) -> str | None:
    """The Apify token: the configured one, or one typed here (optionally saved to the git-ignored .env)."""
    configured = find_token()
    if configured:
        st.success("Token de Apify configurado.", icon=":material/key:")
        other = st.text_input("Usar otro token (opcional)", type="password", key=f"{key}_other")
        return other.strip() or configured
    st.info(f"Hace falta un token de Apify (cuenta gratuita, sin tarjeta): [consíguelo aquí]({APIFY_TOKENS_PAGE}).",
            icon=":material/key:")
    typed = st.text_input("Token de Apify", type="password", key=f"{key}_token").strip()
    if typed and st.checkbox("Guardarlo en .env para la próxima vez", value=True, key=f"{key}_save"):
        st.session_state[f"{key}_save_token"] = typed
    return typed or None


def remember_token(key: str) -> None:
    """Save the token typed in the dialog `key`, if the user asked to."""
    token = st.session_state.pop(f"{key}_save_token", None)
    if token:
        save_token(token)


DOLLAR = r"\$"  # Streamlit reads $...$ as a formula: dollar signs in markdown must be escaped


def markdown_safe(message: str) -> str:
    return message.replace("$", DOLLAR)


def cost_notice(token: str | None, reviews: int) -> None:
    """Estimated cost of downloading `reviews` reviews and the credit left this month."""
    estimate = estimated_cost_usd(reviews)
    st.caption(f"Coste estimado: **~{decimal(estimate)} {DOLLAR}** del crédito de Apify "
               f"(0,0006 {DOLLAR} por reseña en el plan gratuito).")
    credit = apify_credit(token) if token else None
    if token and credit is None:
        st.error("No se ha podido consultar Apify con ese token.")
    elif credit:
        st.caption(f"Crédito disponible este mes: **{decimal(credit['remaining'])} {DOLLAR}** de "
                   f"{decimal(credit['limit'])} {DOLLAR} (se renueva el {pd.Timestamp(credit['cycle_end']):%d/%m/%Y}).")
        if estimate > credit["remaining"]:
            affordable = int(max(0.0, credit["remaining"] - 0.0001) / 0.0006)
            st.warning(f"No hay crédito para tantas reseñas: Apify se detendrá al agotarlo y descargará unas "
                       f"{thousands(affordable)}. Sin tarjeta en la cuenta no se cobra nada más.")
