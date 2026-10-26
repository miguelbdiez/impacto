"""Manual update: download the reviews published since the newest one stored (decision D-022).

For every place in the database, or only the one given, downloads at most --max-reviews new reviews
with Apify, imports and classifies them. Uses Apify credit: about $0.0006 per review on the free plan.

Usage:
    uv run pipeline/update_reviews.py [--place-id ChIJ...] [--max-reviews 100]
"""

import argparse

from sqlalchemy import text

from impacto import database
from impacto.pipeline import update_place


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--place-id", help="update only this place (Google place id)")
    parser.add_argument("--max-reviews", type=int, default=100, help="maximum new reviews per place")
    args = parser.parse_args()

    engine = database.connect()
    with engine.connect() as connection:
        places = connection.execute(text("SELECT place_id, name FROM places ORDER BY name")).all()
    for place in places:
        if args.place_id and place.place_id != args.place_id:
            continue
        print(f"Updating {place.name}")
        update_place(engine, place.place_id, args.max_reviews)


if __name__ == "__main__":
    main()
