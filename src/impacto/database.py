"""Local database of places, reviews and predictions (decision D-018).

SQLite for now, a single file in data/ (git-ignored). The SQL is kept standard so it can move to
PostgreSQL when the app runs in Docker. Only what the analysis needs is stored: no reviewer data,
no review photos and no text of the owner's replies (D-001, D-013).
"""

import sqlite3
from collections.abc import Iterable
from pathlib import Path

DEFAULT_PATH = Path("data/impacto.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS places (
    place_id      TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    address       TEXT,
    city          TEXT,
    category      TEXT,
    latitude      REAL,
    longitude     REAL,
    rating        REAL,
    reviews_count INTEGER,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    place_url     TEXT,
    since         TEXT,
    reviews       INTEGER,
    cost_usd      REAL
);

CREATE TABLE IF NOT EXISTS reviews (
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
    scraped_at          TEXT
);

CREATE INDEX IF NOT EXISTS reviews_place_date ON reviews (place_id, published_at);

CREATE TABLE IF NOT EXISTS predictions (
    review_id    TEXT NOT NULL REFERENCES reviews (review_id),
    model        TEXT NOT NULL,
    probability  REAL NOT NULL,
    label        TEXT NOT NULL,
    threshold    REAL NOT NULL,
    predicted_at TEXT NOT NULL,
    PRIMARY KEY (review_id, model)
);
"""


def connect(path: Path = DEFAULT_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def save_place(connection: sqlite3.Connection, item: dict) -> None:
    """Place details as they come with every Apify review item."""
    location = item.get("location") or {}
    connection.execute(
        """INSERT INTO places VALUES (:place_id, :name, :address, :city, :category, :latitude, :longitude,
                                      :rating, :reviews_count, :updated_at)
           ON CONFLICT (place_id) DO UPDATE SET name = excluded.name, address = excluded.address,
               city = excluded.city, category = excluded.category, latitude = excluded.latitude,
               longitude = excluded.longitude, rating = excluded.rating,
               reviews_count = excluded.reviews_count, updated_at = excluded.updated_at""",
        {"place_id": item["placeId"], "name": item.get("title"), "address": item.get("address"),
         "city": item.get("city"), "category": item.get("categoryName"), "latitude": location.get("lat"),
         "longitude": location.get("lng"), "rating": item.get("totalScore"),
         "reviews_count": item.get("reviewsCount"), "updated_at": item.get("scrapedAt")})


def save_run(connection: sqlite3.Connection, run: dict) -> None:
    connection.execute(
        """INSERT OR REPLACE INTO runs VALUES (:run_id, :source, :downloaded_at, :place_url, :since,
                                               :reviews, :cost_usd)""",
        {"source": "apify", **{key: run.get(key) for key in
                               ("run_id", "downloaded_at", "place_url", "since", "reviews", "cost_usd")}})


def primary_language(code: str | None) -> str | None:
    """'es-ES' -> 'es', 'zh-Hans' -> 'zh': the regional variants are not needed for the analysis."""
    return code.split("-")[0].lower() if code else None


def save_reviews(connection: sqlite3.Connection, items: Iterable[dict], run_id: str | None) -> int:
    """Insert or update Apify review items. Returns how many were new."""
    before = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    for item in items:
        save_place(connection, item)
        connection.execute(
            """INSERT INTO reviews VALUES (:review_id, :place_id, :published_at, :stars, :text, :language,
                                           :text_translated, :translated_language, :likes,
                                           :owner_replied_at, :origin, :run_id, :scraped_at)
               ON CONFLICT (review_id) DO UPDATE SET text = excluded.text, likes = excluded.likes,
                   owner_replied_at = excluded.owner_replied_at, scraped_at = excluded.scraped_at""",
            {"review_id": item["reviewId"], "place_id": item["placeId"],
             "published_at": item["publishedAtDate"], "stars": item["stars"],
             "text": item.get("text") or None, "language": primary_language(item.get("originalLanguage")),
             "text_translated": item.get("textTranslated"), "translated_language": item.get("translatedLanguage"),
             "likes": item.get("likesCount"), "owner_replied_at": item.get("responseFromOwnerDate"),
             "origin": item.get("reviewOrigin"), "run_id": run_id, "scraped_at": item.get("scrapedAt")})
    connection.commit()
    return connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] - before


def reviews_to_predict(connection: sqlite3.Connection, model: str, language: str = "es") -> list[sqlite3.Row]:
    """Reviews with text in the model's language and no prediction from that model yet."""
    return connection.execute(
        """SELECT review_id, text FROM reviews
           WHERE text IS NOT NULL AND language = ?
             AND review_id NOT IN (SELECT review_id FROM predictions WHERE model = ?)""",
        (language, model)).fetchall()


def save_predictions(connection: sqlite3.Connection, rows: Iterable[dict]) -> None:
    connection.executemany(
        """INSERT OR REPLACE INTO predictions VALUES (:review_id, :model, :probability, :label, :threshold,
                                                      :predicted_at)""", rows)
    connection.commit()
