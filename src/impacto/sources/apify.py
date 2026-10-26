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

# Prices measured on the free plan on 2026-10-26 (D-017); paid plans pay less per review
PRICE_PER_REVIEW_USD = 0.0006
PRICE_PER_START_USD = 0.00005

# Fields that identify the author of a review (D-001, D-013)
PERSONAL_FIELDS = {"name", "reviewerId", "reviewerUrl", "reviewerPhotoUrl", "reviewUrl", "userPhotoUrl"}

# Network errors after which a read-only request can simply be repeated
TRANSIENT_ERRORS = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


ENV_FILE = Path(".env")


def find_token(env_file: Path = ENV_FILE) -> str | None:
    """APIFY_TOKEN from the environment or, failing that, from the .env file."""
    token = os.environ.get("APIFY_TOKEN")
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("APIFY_TOKEN="):
                token = line.split("=", 1)[1].strip()
    return token or None


def load_token(env_file: Path = ENV_FILE) -> str:
    token = find_token(env_file)
    if not token:
        raise RuntimeError("APIFY_TOKEN is not set: add it to .env (see README)")
    return token


def save_token(token: str, env_file: Path = ENV_FILE) -> None:
    """Store the token in the git-ignored .env file, replacing a previous one."""
    lines = env_file.read_text(encoding="utf-8-sig").splitlines() if env_file.exists() else []
    lines = [line for line in lines if not line.startswith("APIFY_TOKEN=")] + [f"APIFY_TOKEN={token.strip()}"]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def estimated_cost_usd(reviews: int) -> float:
    return reviews * PRICE_PER_REVIEW_USD + PRICE_PER_START_USD


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
                time.sleep(5 * (attempt + 1))

    def credit(self) -> dict:
        """Monthly credit of the account: limit, used and remaining (USD), and when the cycle ends."""
        data = self._get("users/me/limits")["data"]
        limit = data["limits"]["maxMonthlyUsageUsd"]
        used = data["current"]["monthlyUsageUsd"]
        return {"limit": limit, "used": used, "remaining": max(0.0, limit - used),
                "cycle_end": data["monthlyUsageCycle"]["endAt"]}

    def start(self, max_reviews: int, max_charge_usd: float, place_url: str | None = None,
              place_id: str | None = None, since: str | None = None, language: str = "es") -> dict:
        """Start a run for the newest reviews of one place, given by URL or by Google place id, optionally
        only those published since `since` (YYYY-MM-DD).

        Never retried: a repeated POST would start, and charge, a second run."""
        actor_input = {
            "reviewsSort": "newest",
            "maxReviews": max_reviews,
            "language": language,
            "personalData": False,
        }
        if place_id:
            actor_input["placeIds"] = [place_id]
        else:
            actor_input["startUrls"] = [{"url": place_url}]
        if since:
            actor_input["reviewsStartDate"] = since
        return self._send(f"acts/{ACTOR}/runs?maxItems={max_reviews}&maxTotalChargeUsd={max_charge_usd}",
                          actor_input)["data"]

    def wait(self, run_id: str, on_progress=print) -> dict:
        """Wait until the run finishes, reporting progress as text through `on_progress`."""
        while True:
            # waitForFinish keeps the request open up to 60 s until the run ends
            run = self._get(f"actor-runs/{run_id}?waitForFinish=60")["data"]
            if run["status"] in FINISHED:
                return run
            scraped = (run.get("chargedEventCounts") or {}).get("review-scraped", 0)
            on_progress(f"{run['status']}: {scraped} reviews so far, ${charged_usd(run):.2f}")

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

        # Apify adds the per-review charges a few seconds after the run finishes: wait until they match the
        # reviews downloaded, so the cost recorded is the real one and not just the start fee
        for _ in range(15):
            if (run.get("chargedEventCounts") or {}).get("review-scraped", 0) >= len(items):
                break
            time.sleep(2)
            run = self._get(f"actor-runs/{run['id']}")["data"]
        return Run(id=run["id"], status=run["status"], cost_usd=charged_usd(run), reviews=reviews)
