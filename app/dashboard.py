"""Dashboard of one business (decisions D-020, D-022).

Star statistics use every review; model statistics use the reviews with text in Spanish, and the page
says which is which.
"""

import altair as alt
import pandas as pd
import streamlit as st

from common import (apify_token, chart_config, colors, cost_notice, decimal, markdown_safe, percent, reload,
                    remember_token, thousands)
from impacto import analysis, database
from impacto.pipeline import update_place

FREQUENCIES = {"Mes": "M", "Trimestre": "Q", "Año": "Y"}
MODEL_MEASURE = "Según el modelo (texto en español)"
STARS_MEASURE = "Según las estrellas (1–2★, todas)"
LABELS = {"Good": "Buena", "Bad": "Mala"}
STAR_ORDER = ["5★", "4★", "3★", "2★", "1★"]


def period_label(period: pd.Timestamp, frequency: str) -> str:
    if frequency == "Y":
        return f"{period.year}"
    if frequency == "Q":
        return f"{period.year} T{(period.month - 1) // 3 + 1}"
    return f"{period.year}-{period.month:02d}"


@st.dialog("Actualizar reseñas")
def update_reviews(place: pd.Series, newest: pd.Timestamp) -> None:
    st.markdown(f"Se descargan las reseñas de **{place['name']}** publicadas desde el **{newest:%d/%m/%Y}**, "
                f"fecha de la más reciente guardada, y se clasifican con el modelo.")
    reviews = st.number_input("Máximo de reseñas nuevas", min_value=10, value=100, step=50)
    token = apify_token("update")
    cost_notice(token, reviews)
    if st.button("Actualizar", type="primary", icon=":material/sync:", disabled=not token):
        remember_token("update")
        with st.status("Buscando reseñas nuevas…", expanded=True) as status:
            try:
                summary = update_place(database.connect(), place["place_id"], reviews, token=token,
                                       on_progress=lambda message: status.write(markdown_safe(message)))
            except Exception as error:
                status.update(label="No se ha podido actualizar", state="error")
                st.error(str(error))
                return
            status.update(label=f"{summary['reviews']} reseñas descargadas", state="complete")
        reload()
        st.rerun()


def header(place: pd.Series, reviews: pd.DataFrame) -> None:
    back, _, update = st.columns([1, 4, 1])
    if back.button("Inicio", icon=":material/arrow_back:"):
        del st.query_params["place"]
        st.rerun()
    if update.button("Actualizar reseñas", icon=":material/sync:", width="stretch"):
        update_reviews(place, reviews["published_at"].max())

    groups = reviews["group"].value_counts()
    rating = f"nota en Google {decimal(place['rating'], 1)}★" if pd.notna(place["rating"]) else "sin nota en Google"
    total = f" sobre {thousands(int(place['reviews_count']))} reseñas en total" if pd.notna(place["reviews_count"]) else ""
    st.title(f"{place['name']}: qué opinan sus clientes")
    st.caption(
        f"{thousands(len(reviews))} reseñas de Google entre el {reviews['published_at'].min():%d/%m/%Y} y el "
        f"{reviews['published_at'].max():%d/%m/%Y} · {rating}{total}. Las estadísticas de estrellas usan todas las "
        f"reseñas; el modelo solo puede leer las **{thousands(groups.get(analysis.SPANISH_TEXT, 0))} con texto en "
        f"español**. El resto solo tiene estrellas ({thousands(groups.get(analysis.STARS_ONLY, 0))}) o está en otro "
        f"idioma ({thousands(groups.get(analysis.OTHER_LANGUAGE, 0))}).")


def last_twelve_months(reviews: pd.DataFrame) -> None:
    headline = analysis.last_months(reviews)
    current, previous = headline["current"], headline["previous"]
    st.subheader(f"Últimos 12 meses (hasta el {headline['end']:%d/%m/%Y})")
    st.caption("Comparados con los 12 meses anteriores." if previous["reviews"]
               else "No hay reseñas de los 12 meses anteriores para comparar.")

    def delta(value: float, suffix: str = "", scale: float = 1, digits: int = 1) -> str | None:
        return None if pd.isna(value) or not previous["reviews"] else f"{scale * value:+.{digits}f}{suffix}".replace(".", ",")

    tiles = st.columns(4)
    tiles[0].metric("Reseñas", thousands(current["reviews"]),
                    delta=delta(current["reviews"] - previous["reviews"], digits=0), delta_color="off")
    tiles[1].metric("Nota media", f"{decimal(current['mean_stars'])}★",
                    delta=delta(current["mean_stars"] - previous["mean_stars"], digits=2))
    tiles[2].metric("Malas según el modelo", percent(current["bad_share"]),
                    delta=delta(current["bad_share"] - previous["bad_share"], " pts", 100), delta_color="inverse",
                    help="Reseñas con texto en español que el modelo clasifica como malas.")
    tiles[3].metric("Con 1–2★", percent(current["low_stars_share"]),
                    delta=delta(current["low_stars_share"] - previous["low_stars_share"], " pts", 100),
                    delta_color="inverse", help="Todas las reseñas, con o sin texto.")


def filters(reviews: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """One row of filters above every chart they scope: period and grouping."""
    months = pd.period_range(reviews["published_at"].min().tz_localize(None).to_period("M"),
                             reviews["published_at"].max().tz_localize(None).to_period("M"), freq="M")
    left, right = st.columns([3, 1])
    frequency_name = right.segmented_control("Agrupar por", list(FREQUENCIES), default="Trimestre") or "Trimestre"
    if len(months) < 2:
        return reviews, FREQUENCIES[frequency_name]
    start, end = left.select_slider("Periodo", options=list(months), value=(months[0], months[-1]),
                                    format_func=lambda month: f"{month.month:02d}/{month.year}")
    in_range = reviews["published_at"].dt.tz_localize(None).dt.to_period("M").between(start, end)
    return reviews[in_range], FREQUENCIES[frequency_name]


def evolution(selected: pd.DataFrame, frequency: str) -> None:
    palette = colors()
    st.subheader("¿Cómo evolucionan las opiniones?")
    trend = analysis.evolution(selected, frequency)
    trend["period_label"] = trend["period"].map(lambda period: period_label(period, frequency))
    order = list(trend["period_label"])
    long = trend.melt(id_vars=["period_label", "reviews", "classified"], value_vars=["bad_pct", "low_stars_pct"],
                      var_name="measure", value_name="value")
    long["measure"] = long["measure"].map({"bad_pct": MODEL_MEASURE, "low_stars_pct": STARS_MEASURE})
    long = long.dropna(subset=["value"])

    x = alt.X("period_label:O", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelOverlap=True))
    color = alt.Color("measure:N", scale=alt.Scale(domain=[MODEL_MEASURE, STARS_MEASURE],
                                                   range=[palette["model"], palette["stars"]]))
    hover = alt.selection_point(fields=["period_label"], nearest=True, on="pointerover", empty=False)
    base = alt.Chart(long).encode(x=x, y=alt.Y("value:Q", title="% de reseñas malas"), color=color)
    lines = base.mark_line(strokeWidth=2, strokeCap="round", strokeJoin="round", point=len(order) == 1)
    dots = base.mark_circle(size=70, stroke=palette["surface"], strokeWidth=2).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)))
    crosshair = alt.Chart(trend).mark_rule(color=palette["axis"]).encode(
        x=x, opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("period_label:N", title="Periodo"),
                 alt.Tooltip("bad_pct:Q", title="Malas según el modelo (%)", format=".1f"),
                 alt.Tooltip("low_stars_pct:Q", title="Con 1–2★ (%)", format=".1f"),
                 alt.Tooltip("classified:Q", title="Reseñas leídas por el modelo"),
                 alt.Tooltip("reviews:Q", title="Reseñas totales")]).add_params(hover)
    end_labels = base.transform_filter(alt.datum.period_label == order[-1]).mark_text(align="left", dx=8).encode(
        text=alt.Text("value:Q", format=".0f"), color=alt.value(palette["text"]))
    st.altair_chart(chart_config((lines + dots + crosshair + end_labels).properties(height=320)), width="stretch")
    st.caption("Pasa el ratón por el gráfico para ver los valores. El primer y el último periodo pueden estar "
               "incompletos. Con pocas reseñas por periodo (agrupando por mes) la línea es más irregular.")

    volume = alt.Chart(trend).mark_bar(
        color=palette["context"], cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
        size=24 if len(trend) <= 25 else max(4, int(600 / len(trend)))).encode(
        x=x, y=alt.Y("reviews:Q", title="Reseñas"),
        tooltip=[alt.Tooltip("period_label:N", title="Periodo"), alt.Tooltip("reviews:Q", title="Reseñas"),
                 alt.Tooltip("mean_stars:Q", title="Nota media", format=".2f")])
    st.caption("Número de reseñas por periodo")
    st.altair_chart(chart_config(volume.properties(height=160)), width="stretch")

    with st.expander("Ver los datos de la evolución"):
        st.dataframe(trend[["period_label", "reviews", "mean_stars", "low_stars_pct", "classified", "bad_pct"]]
                     .rename(columns={"period_label": "Periodo", "reviews": "Reseñas", "mean_stars": "Nota media",
                                      "low_stars_pct": "Con 1–2★ (%)", "classified": "Leídas por el modelo",
                                      "bad_pct": "Malas según el modelo (%)"}).round(2),
                     hide_index=True, width="stretch")


def who_writes(selected: pd.DataFrame) -> None:
    st.subheader("¿Quién escribe?")
    by_group = (selected.groupby("group")
                .agg(reviews=("review_id", "size"), mean_stars=("stars", "mean"),
                     low_stars=("stars", lambda stars: (stars <= 2).mean() * 100))
                .reindex([analysis.SPANISH_TEXT, analysis.OTHER_LANGUAGE, analysis.STARS_ONLY]).dropna())
    if {analysis.SPANISH_TEXT, analysis.STARS_ONLY} <= set(by_group.index):
        written, stars_only = by_group.loc[analysis.SPANISH_TEXT], by_group.loc[analysis.STARS_ONLY]
        comparison = "se queja más" if written["low_stars"] > stars_only["low_stars"] else "no se queja más"
        st.markdown(
            f"Quien escribe {comparison}: el **{written['low_stars']:.0f}%** de las reseñas con texto en español "
            f"tienen 1–2★, frente al **{stars_only['low_stars']:.0f}%** de las que solo tienen estrellas. Las "
            f"estadísticas del modelo solo leen texto, así que pueden diferir de la nota de Google.")
    st.dataframe(by_group.reset_index(), hide_index=True, width="content", column_config={
        "group": st.column_config.TextColumn("Tipo de reseña"),
        "reviews": st.column_config.NumberColumn("Reseñas", format="%d"),
        "mean_stars": st.column_config.NumberColumn("Nota media", format="%.2f★"),
        "low_stars": st.column_config.NumberColumn("Con 1–2★", format="%.1f%%")})


def model_vs_stars(selected: pd.DataFrame) -> None:
    palette = colors()
    st.subheader("¿Coincide el modelo con las estrellas?")
    counts = analysis.stars_vs_model(selected)
    if counts.empty:
        st.info("No hay reseñas con texto en español en este periodo.")
        return
    check = analysis.agreement(selected)
    left, right = st.columns([1, 2])
    left.metric("Coincidencia con las estrellas", percent(check["accuracy"]),
                help="Reseñas con texto en español y 1–2★ (deberían ser malas) o 4–5★ (deberían ser buenas). "
                     "Las de 3★ se dejan fuera.")
    left.caption(f"Sobre {thousands(check['reviews'])} reseñas. Detecta el {percent(check['recall_bad'])} de las de "
                 f"1–2★ como malas y el {percent(check['recall_good'])} de las de 4–5★ como buenas. El modelo se "
                 f"entrenó con reseñas de productos de Amazon, no de este negocio.")

    shares = counts.melt(id_vars=["stars", "total"], value_vars=["Good", "Bad"], var_name="label", value_name="count")
    shares["share"] = shares["count"] / shares["total"]
    shares["label_es"] = shares["label"].map(LABELS)
    shares["stars_label"] = shares["stars"].map(lambda stars: f"{stars}★")
    bars = alt.Chart(shares).encode(
        y=alt.Y("stars_label:O", sort=STAR_ORDER, title=None),
        x=alt.X("share:Q", stack="normalize", title="Clasificación del modelo", axis=alt.Axis(format="%")),
        color=alt.Color("label_es:N", scale=alt.Scale(domain=["Buena", "Mala"],
                                                      range=[palette["good"], palette["bad"]])),
        order=alt.Order("label:N", sort="descending"),
        tooltip=[alt.Tooltip("stars_label:N", title="Estrellas"), alt.Tooltip("label_es:N", title="Modelo"),
                 alt.Tooltip("count:Q", title="Reseñas"), alt.Tooltip("share:Q", title="Porcentaje", format=".0%")])
    segments = bars.mark_bar(size=22, stroke=palette["surface"], strokeWidth=2)
    # Labels inside a segment only where they fit: stack first (same order as the bars), then filter
    inside = (alt.Chart(shares)
              .transform_stack(stack="share", groupby=["stars_label"], as_=["start", "end"],
                               sort=[alt.SortField("label", "descending")], offset="normalize")
              .transform_filter(alt.datum.share >= 0.12)
              .transform_calculate(middle="(datum.start + datum.end) / 2")
              .mark_text(color="#ffffff")
              .encode(y=alt.Y("stars_label:O", sort=STAR_ORDER), x=alt.X("middle:Q"),
                      text=alt.Text("share:Q", format=".0%")))
    # A fixed step per row keeps the 22px bars from overlapping
    right.altair_chart(chart_config((segments + inside).properties(height=alt.Step(36))), width="stretch")


def topics(selected: pd.DataFrame) -> None:
    palette = colors()
    st.subheader("¿De qué hablan?")
    st.caption("Palabras que más distinguen las reseñas que el modelo clasifica como malas de las buenas (y al revés), "
               "y el porcentaje de reseñas en que aparecen. Solo reseñas con texto en español.")
    words = analysis.distinctive_words(selected)
    if words.empty:
        st.info("Hacen falta más reseñas con texto en español para encontrar palabras características.")
        return
    left, right = st.columns(2)
    for column, side, share, title in ((left, "Bad", "bad_pct", "Reseñas malas"),
                                       (right, "Good", "good_pct", "Reseñas buenas")):
        side_words = words[words["side"] == side]
        chart = alt.Chart(side_words).mark_bar(
            color=palette["bad" if side == "Bad" else "good"], size=16, cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4).encode(
            y=alt.Y("word:N", sort=list(side_words["word"]), title=None),
            x=alt.X(f"{share}:Q", title=f"% de {title.lower()} que la mencionan", axis=alt.Axis(tickCount=4)),
            tooltip=[alt.Tooltip("word:N", title="Palabra"),
                     alt.Tooltip("bad_pct:Q", title="% de reseñas malas", format=".1f"),
                     alt.Tooltip("good_pct:Q", title="% de reseñas buenas", format=".1f")])
        labels = chart.mark_text(align="left", dx=4, color=palette["text"]).encode(
            text=alt.Text(f"{share}:Q", format=".0f"))
        column.markdown(f"**{title}**")
        column.altair_chart(chart_config((chart + labels).properties(height=380)), width="stretch")


def examples(selected: pd.DataFrame) -> None:
    st.subheader("Ejemplos")
    kinds = {"Malas más recientes": "bad", "Buenas más recientes": "good",
             "4–5★ que el modelo ve malas": "high_stars_bad", "1–2★ que el modelo ve buenas": "low_stars_good"}
    kind = st.segmented_control("Mostrar", list(kinds), default="Malas más recientes") or "Malas más recientes"
    chosen = analysis.examples(selected, kinds[kind])
    if chosen.empty:
        st.caption("No hay ejemplos de este tipo en el periodo elegido.")
    # A list instead of a table: the excerpts are the point, and table cells would cut them
    for example in chosen.itertuples():
        st.markdown(f"**{example.stars}★** · {example.date:%d/%m/%Y} · probabilidad de buena según el modelo: "
                    f"{decimal(example.probability_good)}\n> {example.excerpt}")
    st.caption("Fragmentos cortos de reseñas públicas de Google. No se guarda ningún dato de sus autores.")


def render(place: pd.Series, reviews: pd.DataFrame) -> None:
    header(place, reviews)
    last_twelve_months(reviews)
    st.divider()
    selected, frequency = filters(reviews)
    evolution(selected, frequency)
    who_writes(selected)
    model_vs_stars(selected)
    topics(selected)
    examples(selected)
