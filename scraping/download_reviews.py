"""Download the Google Maps reviews of a place with Apify (decision D-017).

Saves the reviews (without reviewer data) and a summary of the run, including its real cost, to
data/reviews/. Import them afterwards with pipeline/import_reviews.py. The defaults keep every run small
and cheap; raise --max-reviews and --max-charge-usd only if you are willing to use more Apify credit.

Usage:
    uv run scraping/download_reviews.py --max-reviews 50 --max-charge-usd 0.2
    uv run scraping/download_reviews.py --run-id <id>    # resume a run that is running or finished

A run keeps going on Apify even if this program stops (for example after a network error). Resume it
with --run-id instead of starting a new one, which would be charged again.
"""

import argparse
import json

from impacto.pipeline import save_download
from impacto.sources.apify import ApifyReviews

# El Corte Inglés Princesa (Edificio Moda), Madrid (D-001 update)
DEFAULT_PLACE = ("https://www.google.com/maps/place/El+Corte+Ingl%C3%A9s+Princesa+Edificio+Moda/"
                 "@40.4304842,-3.7157889,17z/data=!3m1!4b1!4m6!3m5!1s0xd4228691ebfe55f:0x18ee6bfd6a626b22"
                 "!8m2!3d40.4304842!4d-3.7157889!16s%2Fg%2F11bbwm95g6")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--place-url", default=DEFAULT_PLACE)
    parser.add_argument("--since", default="2019-01-01", help="oldest publication date (YYYY-MM-DD)")
    parser.add_argument("--max-reviews", type=int, default=50)
    parser.add_argument("--max-charge-usd", type=float, default=0.2, help="maximum Apify charge for this run")
    parser.add_argument("--run-id", help="resume this run instead of starting a new one")
    args = parser.parse_args()

    client = ApifyReviews()
    if args.run_id:
        run_id = args.run_id
        print(f"Resuming run {run_id}")
    else:
        print(f"Starting the Apify actor: up to {args.max_reviews} reviews since {args.since}, "
              f"at most ${args.max_charge_usd}")
        run_id = client.start(args.max_reviews, args.max_charge_usd, place_url=args.place_url,
                              since=args.since)["id"]
        print(f"Run {run_id} started (resume it with --run-id {run_id} if this program stops)")

    summary = save_download(client.fetch(client.wait(run_id)), args.place_url, args.since)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
