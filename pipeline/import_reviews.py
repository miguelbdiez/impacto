"""Load downloaded reviews (data/reviews/) into the local database (decision D-018).

Each download is a pair of files written by scraping/download_reviews.py: reviews_<stamp>.json and
run_<stamp>.json. Importing is idempotent: reviews already in the database are updated, not
duplicated, so a download can be imported again safely.

Usage:
    uv run pipeline/import_reviews.py [--reviews-dir data/reviews] [--database data/impacto.db]
"""

import argparse
import json
from pathlib import Path

from impacto.database import DEFAULT_PATH, connect, save_reviews, save_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reviews-dir", type=Path, default=Path("data/reviews"))
    parser.add_argument("--database", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    connection = connect(args.database)
    for reviews_file in sorted(args.reviews_dir.glob("reviews_*.json")):
        run_file = reviews_file.with_name(reviews_file.name.replace("reviews_", "run_"))
        run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
        if run:
            save_run(connection, run)
        items = json.loads(reviews_file.read_text(encoding="utf-8"))
        new = save_reviews(connection, items, run.get("run_id"))
        print(f"{reviews_file.name}: {len(items)} reviews, {new} new")

    total, with_text, spanish = connection.execute(
        """SELECT COUNT(*), COUNT(text), SUM(text IS NOT NULL AND language = 'es') FROM reviews""").fetchone()
    print(f"Database {args.database}: {total} reviews, {with_text} with text, {spanish} with text in Spanish")


if __name__ == "__main__":
    main()
