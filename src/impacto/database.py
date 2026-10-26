"""Database of places, reviews and predictions (decisions D-018, D-021).

SQLite by default (data/impacto.db, git-ignored) and PostgreSQL when DATABASE_URL points to it, as in
Docker. Tables and queries are standard SQL shared by both; only the reporting view for Power BI has one
version per engine, because date functions differ. Only what the analysis needs is stored: no reviewer
data, no review photos and no text of the owner's replies (D-001, D-013).
"""

import os
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import Connection, Engine, create_engine, event, text

DEFAULT_URL = "sqlite:///data/impacto.db"
MODEL = "model_c"

TABLES = [
    """CREATE TABLE IF NOT EXISTS places (
        place_id      TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        address       TEXT,
        city          TEXT,
        category      TEXT,
        latitude      REAL,
        longitude     REAL,
        rating        REAL,
        reviews_count INTEGER,
        updated_at    TEXT)""",
    """CREATE TABLE IF NOT EXISTS runs (
        run_id        TEXT PRIMARY KEY,
        source        TEXT NOT NULL,
        downloaded_at TEXT NOT NULL,
        place_url     TEXT,
        since         TEXT,
        reviews       INTEGER,
        cost_usd      REAL)""",
    """CREATE TABLE IF NOT EXISTS reviews (
        review_id           TEXT PRIMARY KEY,
        place_id            TEXT NOT NULL REFERENCES places (place_id),
        published_at        TEXT NOT NULL,
        stars               INTEGER NOT NULL,
        text                TEXT,
        language            TEXT,
        text_translated     TEXT,
        translated_language TEXT,
        likes               INTEGER,
        owner_replied_at    TEXT,
        origin              TEXT,
        run_id              TEXT REFERENCES runs (run_id),
        scraped_at          TEXT)""",
    "CREATE INDEX IF NOT EXISTS reviews_place_date ON reviews (place_id, published_at)",
    """CREATE TABLE IF NOT EXISTS predictions (
        review_id    TEXT NOT NULL REFERENCES reviews (review_id),
        model        TEXT NOT NULL,
        probability  REAL NOT NULL,
        label        TEXT NOT NULL,
        threshold    REAL NOT NULL,
        predicted_at TEXT NOT NULL,
        PRIMARY KEY (review_id, model))""",
]

# One row per review with everything a report needs, for Power BI (D-023). Dates are real dates in
# PostgreSQL; SQLite has no date type, so there they stay as ISO text.
REPORT_COLUMNS = """
    r.review_id, r.place_id, p.name AS place_name, {published_at} AS published_at,
    {published_date} AS published_date, {published_month} AS published_month, r.stars,
    CASE WHEN r.stars <= 2 THEN 1 ELSE 0 END AS low_stars,
    CASE WHEN r.text IS NULL THEN 'Solo estrellas'
         WHEN r.language = 'es' THEN 'Texto en español'
         ELSE 'Texto en otro idioma' END AS review_group,
    r.language, pr.label AS model_label, pr.probability AS model_probability,
    CASE WHEN pr.label = 'Bad' THEN 1 WHEN pr.label = 'Good' THEN 0 END AS model_bad, r.likes, r.text
FROM reviews r
JOIN places p ON p.place_id = r.place_id
LEFT JOIN predictions pr ON pr.review_id = r.review_id AND pr.model = '{model}'"""

REPORT_VIEW = {
    "postgresql": ["CREATE OR REPLACE VIEW review_facts AS SELECT" + REPORT_COLUMNS.format(
        published_at="CAST(r.published_at AS timestamptz)",
        published_date="CAST(CAST(r.published_at AS timestamptz) AS date)",
        published_month="CAST(date_trunc('month', CAST(r.published_at AS timestamptz)) AS date)",
        model=MODEL)],
    "sqlite": ["DROP VIEW IF EXISTS review_facts",
               "CREATE VIEW review_facts AS SELECT" + REPORT_COLUMNS.format(
                   published_at="r.published_at", published_date="substr(r.published_at, 1, 10)",
                   published_month="substr(r.published_at, 1, 7) || '-01'", model=MODEL)],
}


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def connect(url: str | None = None) -> Engine:
    """Engine for the database, with the tables and the report view created if missing."""
    url = url or database_url()
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        # SQLite checks foreign keys only when asked to, PostgreSQL always does
        event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys = ON"))
    with engine.begin() as connection:
        for statement in TABLES + REPORT_VIEW[engine.dialect.name]:
            connection.execute(text(statement))
    return engine


def primary_language(code: str | None) -> str | None:
    """'es-ES' -> 'es', 'zh-Hans' -> 'zh': the regional variants are not needed for the analysis."""
    return code.split("-")[0].lower() if code else None


def save_place(connection: Connection, item: dict) -> None:
    """Place details as they come with every Apify review item."""
    location = item.get("location") or {}
    connection.execute(text(
        """INSERT INTO places VALUES (:place_id, :name, :address, :city, :category, :latitude, :longitude,
                                      :rating, :reviews_count, :updated_at)
           ON CONFLICT (place_id) DO UPDATE SET name = excluded.name, address = excluded.address,
               city = excluded.city, category = excluded.category, latitude = excluded.latitude,
               longitude = excluded.longitude, rating = excluded.rating,
               reviews_count = excluded.reviews_count, updated_at = excluded.updated_at"""),
        {"place_id": item["placeId"], "name": item.get("title"), "address": item.get("address"),
         "city": item.get("city"), "category": item.get("categoryName"), "latitude": location.get("lat"),
         "longitude": location.get("lng"), "rating": item.get("totalScore"),
         "reviews_count": item.get("reviewsCount"), "updated_at": item.get("scrapedAt")})


def save_run(connection: Connection, run: dict) -> None:
    connection.execute(text(
        """INSERT INTO runs VALUES (:run_id, :source, :downloaded_at, :place_url, :since, :reviews, :cost_usd)
           ON CONFLICT (run_id) DO UPDATE SET downloaded_at = excluded.downloaded_at,
               reviews = excluded.reviews, cost_usd = excluded.cost_usd"""),
        {"source": "apify", **{key: run.get(key) for key in
                               ("run_id", "downloaded_at", "place_url", "since", "reviews", "cost_usd")}})


def imported_runs(connection: Connection) -> set[str]:
    return set(connection.execute(text("SELECT run_id FROM runs")).scalars())


def save_reviews(connection: Connection, items: Iterable[dict], run_id: str | None) -> int:
    """Insert or update Apify review items. Returns how many were new."""
    count = text("SELECT COUNT(*) FROM reviews")
    before = connection.execute(count).scalar()
    for item in items:
        save_place(connection, item)
        connection.execute(text(
            """INSERT INTO reviews VALUES (:review_id, :place_id, :published_at, :stars, :text, :language,
                                           :text_translated, :translated_language, :likes,
                                           :owner_replied_at, :origin, :run_id, :scraped_at)
               ON CONFLICT (review_id) DO UPDATE SET text = excluded.text, likes = excluded.likes,
                   owner_replied_at = excluded.owner_replied_at, scraped_at = excluded.scraped_at"""),
            {"review_id": item["reviewId"], "place_id": item["placeId"],
             "published_at": item["publishedAtDate"], "stars": item["stars"],
             "text": item.get("text") or None, "language": primary_language(item.get("originalLanguage")),
             "text_translated": item.get("textTranslated"), "translated_language": item.get("translatedLanguage"),
             "likes": item.get("likesCount"), "owner_replied_at": item.get("responseFromOwnerDate"),
             "origin": item.get("reviewOrigin"), "run_id": run_id, "scraped_at": item.get("scrapedAt")})
    return connection.execute(count).scalar() - before


def reviews_to_predict(connection: Connection, model: str, language: str = "es") -> list:
    """Reviews with text in the model's language and no prediction from that model yet."""
    return connection.execute(text(
        """SELECT review_id, text FROM reviews
           WHERE text IS NOT NULL AND language = :language
             AND review_id NOT IN (SELECT review_id FROM predictions WHERE model = :model)"""),
        {"language": language, "model": model}).all()


def save_predictions(connection: Connection, rows: list[dict]) -> None:
    if rows:
        connection.execute(text(
            """INSERT INTO predictions VALUES (:review_id, :model, :probability, :label, :threshold, :predicted_at)
               ON CONFLICT (review_id, model) DO UPDATE SET probability = excluded.probability,
                   label = excluded.label, threshold = excluded.threshold, predicted_at = excluded.predicted_at"""),
            rows)


def delete_place(connection: Connection, place_id: str) -> dict:
    """Remove a place with its reviews and their predictions. Returns the runs it came from and what was deleted."""
    parameters = {"place_id": place_id}
    runs = set(connection.execute(text("SELECT DISTINCT run_id FROM reviews WHERE place_id = :place_id"),
                                  parameters).scalars()) - {None}
    predictions = connection.execute(text(
        "DELETE FROM predictions WHERE review_id IN (SELECT review_id FROM reviews WHERE place_id = :place_id)"),
        parameters).rowcount
    reviews = connection.execute(text("DELETE FROM reviews WHERE place_id = :place_id"), parameters).rowcount
    # A run is deleted only if none of its reviews belongs to another place
    for run_id in runs:
        connection.execute(text("DELETE FROM runs WHERE run_id = :run_id "
                                "AND NOT EXISTS (SELECT 1 FROM reviews WHERE run_id = :run_id)"), {"run_id": run_id})
    connection.execute(text("DELETE FROM places WHERE place_id = :place_id"), parameters)
    return {"runs": runs, "reviews": reviews, "predictions": predictions}


def last_published(connection: Connection, place_id: str) -> str | None:
    """Publication date of the newest review stored for a place (ISO text)."""
    return connection.execute(text("SELECT MAX(published_at) FROM reviews WHERE place_id = :place_id"),
                              {"place_id": place_id}).scalar()
