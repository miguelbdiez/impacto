"""Load downloaded reviews (data/reviews/) into the database (decisions D-018, D-021).

Each download is a pair of files written by the download step: reviews_<stamp>.json and run_<stamp>.json.
Downloads already imported are skipped; --everything imports them again (reviews are updated, never
duplicated). The database is SQLite by default, or the one in DATABASE_URL (PostgreSQL in Docker).

Usage:
    uv run pipeline/import_reviews.py [--everything]
"""

import argparse

from sqlalchemy import text

from impacto import database
from impacto.pipeline import REVIEWS_DIR, import_downloads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--everything", action="store_true", help="import downloads already imported too")
    args = parser.parse_args()

    engine = database.connect()
    for result in import_downloads(engine, REVIEWS_DIR, args.everything):
        print(f"{result['file']}: {result['reviews']} reviews, {result['new']} new")

    with engine.connect() as connection:
        total, with_text, spanish = connection.execute(text(
            """SELECT COUNT(*), COUNT(text), SUM(CASE WHEN text IS NOT NULL AND language = 'es' THEN 1 ELSE 0 END)
               FROM reviews""")).one()
    print(f"Database {engine.url.render_as_string(hide_password=True)}: {total} reviews, {with_text} with text, "
          f"{spanish or 0} with text in Spanish")


if __name__ == "__main__":
    main()
