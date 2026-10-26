"""Google Maps reviews through Apify (decision D-017).

Runs the official actor `compass/google-maps-reviews-scraper` with the Apify REST API, waits for it to
finish and returns the reviews. Every run has a maximum number of reviews and a maximum charge, so a
run can never spend more than intended. On the free plan without a payment method nothing can be
charged at all: Apify stops the runs when the monthly credit is used up.

The actor is asked not to collect personal data of the reviewers (`personalData: false`). Any
reviewer field that still arrives is removed before the reviews leave this module.

A run keeps going on Apify's servers even if this program stops, so a run can be resumed by its id
(`wait` and `fetch`) without starting, and paying for, a new one.
"""

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API = "https://api.apify.com/v2"
ACTOR = "compass~google-maps-reviews-scraper"
FINISHED = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
PAGE_SIZE = 1000
RETRIES = 5

# Fields that identify the author of a review (D-001, D-013)
PERSONAL_FIELDS = {"name", "reviewerId", "reviewerUrl", "reviewerPhotoUrl", "reviewUrl", "userPhotoUrl"}

# Network errors after which a read-only request can simply be repeated
TRANSIENT_ERRORS = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


def load_token(env_file: Path = Path(".env")) -> str:
    """APIFY_TOKEN from the environment or, failing that, from the .env file."""
    token = os.environ.get("APIFY_TOKEN")
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("APIFY_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        raise RuntimeError("APIFY_TOKEN is not set: add it to .env (see CLAUDE.md)")
    return token


def charged_usd(run: dict) -> float:
    """What the run costs: charged events (one per review, one per start) times their price.

    usageTotalUsd is not used because it can be read before the event charges are added."""
    events = (run.get("pricingInfo") or {}).get("pricingPerEvent", {}).get("actorChargeEvents", {})
    return sum(count * events.get(name, {}).get("eventPriceUsd", 0.0)
               for name, count in (run.get("chargedEventCounts") or {}).items())


@dataclass
class Run:
    id: str
    status: str
    cost_usd: float
    reviews: list[dict]


class ApifyReviews:
    def __init__(self, token: str | None = None):
        self.token = token or load_token()

    def _send(self, path: str, body: dict | None = None):
        request = urllib.request.Request(
            f"{API}/{path}",
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="GET" if body is None else "POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)

    def _get(self, path: str):
        """GET with retries: reading is safe to repeat after a network error."""
        for attempt in range(RETRIES):
            try:
                return self._send(path)
            except TRANSIENT_ERRORS as error:
                if attempt == RETRIES - 1:
                    raise
                print(f"  network error ({error.__class__.__name__}), retrying in {5 * (attempt + 1)} s")
                time.sleep(5 * (attempt + 1))

    def start(self, place_url: str, since: str, max_reviews: int, max_charge_usd: float,
              language: str = "es") -> dict:
        """Start a run for the reviews of one place published since `since` (YYYY-MM-DD), newest first.

        Never retried: a repeated POST would start, and charge, a second run."""
        actor_input = {
            "startUrls": [{"url": place_url}],
            "reviewsSort": "newest",
            "reviewsStartDate": since,
            "maxReviews": max_reviews,
            "language": language,
            "personalData": False,
        }
        return self._send(f"acts/{ACTOR}/runs?maxItems={max_reviews}&maxTotalChargeUsd={max_charge_usd}",
                          actor_input)["data"]

    def wait(self, run_id: str) -> dict:
        while True:
            # waitForFinish keeps the request open up to 60 s until the run ends
            run = self._get(f"actor-runs/{run_id}?waitForFinish=60")["data"]
            if run["status"] in FINISHED:
                return run
            scraped = (run.get("chargedEventCounts") or {}).get("review-scraped", 0)
            print(f"  {run['status']}: {scraped} reviews so far, ${charged_usd(run):.2f}")

    def fetch(self, run: dict) -> Run:
        """The reviews of a finished run, without reviewer fields, downloaded in pages."""
        items = []
        while True:
            page = self._get(f"datasets/{run['defaultDatasetId']}/items?clean=true&format=json"
                             f"&offset={len(items)}&limit={PAGE_SIZE}")
            items.extend(page)
            if len(page) < PAGE_SIZE:
                break
        reviews = [{key: value for key, value in item.items() if key not in PERSONAL_FIELDS} for item in items]
        return Run(id=run["id"], status=run["status"], cost_usd=charged_usd(run), reviews=reviews)
