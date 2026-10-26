"""Statistics behind the app (decision D-020).

Every review counts for the star statistics. Only reviews with text in Spanish have a model prediction
(D-019), so every figure based on the model says so. Reviewers who write complain much more than those
who only leave stars: showing the texts alone would make a business look worse than it is.
"""

import math
import re

import pandas as pd
from sqlalchemy import Connection, text

SPANISH_TEXT, OTHER_LANGUAGE, STARS_ONLY = "Texto en español", "Texto en otro idioma", "Solo estrellas"

# Function words left out of the topic analysis. "no" is included on purpose: the goal is to find what
# reviews talk about (parking, staff, prices...), and "no" would top every list of bad reviews.
STOPWORDS = set("""
a al algo algún alguna algunas alguno algunos allí ante antes aquí así aun aunque bastante cada casi como
con contra cual cuando de del desde donde dos e el ella ellas ellos en entre era eran es esa esas ese eso
esos esta está están estaba estado estar estas este esto estos estoy fue fueron gran ha había han has hay
he hemos hace hacer hacen hasta hecho la las le les lo los me mi mis mismo mucha muchas mucho muchos muy
más nada ni no nos nosotros o os otra otras otro otros para pero poco por porque pues que qué quien se
sea ser si sido siempre sin sobre solo son su sus también tan tanto te tener tengo tiene tienen todas
todo todos tu tus un una unas uno unos usted vez y ya yo él ese vas van voy ver veces dia día cosa cosas
corte inglés ingles princesa edificio moda madrid sitio lugar tienda tiendas centro
""".split())

WORD = re.compile(r"[a-záéíóúüñ]+")


def load_reviews(connection: Connection, model: str = "model_c") -> pd.DataFrame:
    reviews = pd.read_sql(text(
        """SELECT r.review_id, r.place_id, r.published_at, r.stars, r.text, r.language, r.likes,
                  r.owner_replied_at, p.probability, p.label
           FROM reviews r LEFT JOIN predictions p ON p.review_id = r.review_id AND p.model = :model"""),
        connection, params={"model": model})
    reviews["published_at"] = pd.to_datetime(reviews["published_at"], utc=True, format="ISO8601")
    reviews["group"] = STARS_ONLY
    reviews.loc[reviews["text"].notna(), "group"] = OTHER_LANGUAGE
    reviews.loc[reviews["text"].notna() & (reviews["language"] == "es"), "group"] = SPANISH_TEXT
    return reviews


def load_places(connection: Connection) -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM places ORDER BY name"), connection)


def bad_share(reviews: pd.DataFrame) -> float:
    """Share of the classified reviews that the model labels as bad (NaN if none is classified)."""
    labels = reviews["label"].dropna()
    return (labels == "Bad").mean() if len(labels) else math.nan


def last_months(reviews: pd.DataFrame, months: int = 12) -> dict:
    """Headline figures for the last `months` months and the same period just before."""
    end = reviews["published_at"].max()
    start = end - pd.DateOffset(months=months)
    windows = {
        "current": reviews[reviews["published_at"] > start],
        "previous": reviews[(reviews["published_at"] <= start)
                            & (reviews["published_at"] > start - pd.DateOffset(months=months))],
    }
    return {"end": end, **{
        name: {"reviews": len(window),
               "mean_stars": window["stars"].mean(),
               "low_stars_share": (window["stars"] <= 2).mean(),
               "bad_share": bad_share(window),
               "classified": window["label"].notna().sum()}
        for name, window in windows.items()}}


def evolution(reviews: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Per month ('M'), quarter ('Q') or year ('Y'): volume, mean stars, share of 1-2 stars (all
    reviews) and share predicted bad (Spanish texts)."""
    period = reviews["published_at"].dt.tz_localize(None).dt.to_period(frequency).dt.start_time
    classified = reviews["label"].notna()
    frame = pd.DataFrame({
        "period": period,
        "stars": reviews["stars"],
        "low_stars": (reviews["stars"] <= 2).astype(float),
        "bad": (reviews["label"] == "Bad").astype(float).where(classified),
    })
    grouped = frame.groupby("period")
    return pd.DataFrame({
        "reviews": grouped.size(),
        "mean_stars": grouped["stars"].mean(),
        "low_stars_pct": grouped["low_stars"].mean() * 100,
        "classified": grouped["bad"].count(),
        "bad_pct": grouped["bad"].mean() * 100,
    }).reset_index()


def stars_vs_model(reviews: pd.DataFrame) -> pd.DataFrame:
    """For each star rating, how many classified reviews the model labels good and bad."""
    classified = reviews[reviews["label"].notna()]
    counts = classified.groupby(["stars", "label"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["Good", "Bad"], fill_value=0)
    counts["total"] = counts.sum(axis=1)
    return counts.reset_index()


def agreement(reviews: pd.DataFrame) -> dict:
    """Model against the stars as labels: 1-2 stars bad, 4-5 stars good (3 stars left out)."""
    polar = reviews[reviews["label"].notna() & (reviews["stars"] != 3)]
    truth = polar["stars"].map(lambda stars: "Good" if stars >= 4 else "Bad")
    correct = truth == polar["label"]
    recall = correct.groupby(truth).mean()
    return {"reviews": len(polar), "accuracy": correct.mean(),
            "recall_bad": recall.get("Bad", math.nan), "recall_good": recall.get("Good", math.nan)}


def words(text: str) -> set[str]:
    """Distinct content words of a review, lowercased, accents kept for display."""
    return {word for word in WORD.findall(text.lower()) if len(word) > 2 and word not in STOPWORDS}


def distinctive_words(reviews: pd.DataFrame, top: int = 15, minimum_reviews: int = 10,
                      prior: float = 500.0) -> pd.DataFrame:
    """Words that set bad reviews apart from good ones, and the other way round.

    Log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi and Quinn, 2008), counting
    each word once per review. The prior shrinks rare words, so a word that appears in two reviews
    cannot top the list. Returns the `top` words of each side with the share of bad and good reviews
    that contain them."""
    classified = reviews[reviews["label"].notna()]
    documents = {label: [words(text) for text in classified.loc[classified["label"] == label, "text"]]
                 for label in ("Bad", "Good")}
    counts = {label: pd.Series([word for document in docs for word in document]).value_counts()
              for label, docs in documents.items()}
    table = pd.DataFrame(counts).fillna(0)
    table = table[table.sum(axis=1) >= minimum_reviews]

    total = table.sum(axis=1)
    alpha = prior * total / total.sum()
    sizes = {label: table[label].sum() for label in ("Bad", "Good")}
    log_odds = {label: ((table[label] + alpha) / (sizes[label] + prior - table[label] - alpha)).map(math.log)
                for label in ("Bad", "Good")}
    variance = 1 / (table["Bad"] + alpha) + 1 / (table["Good"] + alpha)
    table["z"] = (log_odds["Bad"] - log_odds["Good"]) / variance.map(math.sqrt)
    table["bad_pct"] = table["Bad"] / len(documents["Bad"]) * 100
    table["good_pct"] = table["Good"] / len(documents["Good"]) * 100
    table = table.rename_axis("word").reset_index()

    bad = table.nlargest(top, "z").assign(side="Bad")
    good = table.nsmallest(top, "z").assign(side="Good")
    return pd.concat([bad, good], ignore_index=True)


def excerpt(text: str, length: int = 180) -> str:
    """First `length` characters, cut at a word boundary."""
    text = " ".join(text.split())
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


def examples(reviews: pd.DataFrame, kind: str, count: int = 10) -> pd.DataFrame:
    """Most recent classified reviews of one kind, as short excerpts (no reviewer data is stored)."""
    classified = reviews[reviews["label"].notna()]
    selection = {
        "bad": classified["label"] == "Bad",
        "good": classified["label"] == "Good",
        "high_stars_bad": (classified["stars"] >= 4) & (classified["label"] == "Bad"),
        "low_stars_good": (classified["stars"] <= 2) & (classified["label"] == "Good"),
    }[kind]
    chosen = classified[selection].nlargest(count, "published_at")
    return pd.DataFrame({
        "date": chosen["published_at"].dt.date,
        "stars": chosen["stars"],
        "probability_good": chosen["probability"].round(2),
        "excerpt": chosen["text"].map(excerpt),
    })
