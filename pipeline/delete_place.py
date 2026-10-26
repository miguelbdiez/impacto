"""Delete a business: its reviews and predictions in the database and its downloads in data/reviews/.

The downloads go too, otherwise the next import (for example when Docker starts) would load the business again.

Usage:
    uv run pipeline/delete_place.py ChIJ...            # one place, by Google place id
    uv run pipeline/delete_place.py --keep ChIJ...     # every place except this one
"""

import argparse
import json

from sqlalchemy import text

from impacto import database
from impacto.pipeline import REVIEWS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("place_id", nargs="?", help="place to delete")
    parser.add_argument("--keep", help="delete every place except this one")
    args = parser.parse_args()
    if bool(args.place_id) == bool(args.keep):
        parser.error("give either a place id or --keep")

    engine = database.connect()
    with engine.begin() as connection:
        places = connection.execute(text("SELECT place_id, name FROM places")).all()
        targets = [place for place in places
                   if (args.place_id and place.place_id == args.place_id) or (args.keep and place.place_id != args.keep)]
        runs = set()
        for place in targets:
            deleted = database.delete_place(connection, place.place_id)
            runs |= deleted["runs"]
            print(f"{place.name}: {deleted['reviews']} reviews and {deleted['predictions']} predictions deleted")

    # Downloads of the deleted runs, identified by the run id in each summary file
    for run_file in REVIEWS_DIR.glob("run_*.json"):
        if json.loads(run_file.read_text(encoding="utf-8")).get("run_id") in runs:
            reviews_file = run_file.with_name(run_file.name.replace("run_", "reviews_"))
            reviews_file.unlink(missing_ok=True)
            run_file.unlink()
            print(f"Deleted {run_file.name} and {reviews_file.name}")


if __name__ == "__main__":
    main()
