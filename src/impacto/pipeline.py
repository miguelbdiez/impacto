"""Collect, store and classify reviews (decisions D-017, D-018, D-022).

The steps shared by the command-line scripts and the app: download the reviews of a place with Apify,
keep the raw download as JSON in data/reviews/ (Apify deletes results after 7 days), load it into the
database and classify the new Spanish texts with the OpenNN model.
"""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine

from impacto import database
from impacto.model import DEFAULT_MODEL_DIR, SentimentModel
from impacto.sources.apify import ApifyReviews, Run, estimated_cost_usd

REVIEWS_DIR = Path("data/reviews")


def save_download(run: Run, place: str, since: str | None, output_dir: Path = REVIEWS_DIR) -> dict:
    """Write the reviews and a summary of the run (with its real cost) as JSON. Returns the summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (output_dir / f"reviews_{stamp}.json").write_text(json.dumps(run.reviews, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    dates = sorted(review["publishedAtDate"] for review in run.reviews if review.get("publishedAtDate"))
    summary = {
        "run_id": run.id,
        "status": run.status,
        "downloaded_at": stamp,
        "place_url": place,
        "since": since,
        "reviews": len(run.reviews),
        "with_text": sum(bool(review.get("text")) for review in run.reviews),
        "cost_usd": round(run.cost_usd, 5),
        "oldest": dates[0] if dates else None,
        "newest": dates[-1] if dates else None,
        "place_id": run.reviews[0]["placeId"] if run.reviews else None,
        "place_name": run.reviews[0].get("title") if run.reviews else None,
        "languages": dict(Counter(review.get("originalLanguage") for review in run.reviews).most_common()),
    }
    (output_dir / f"run_{stamp}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def import_downloads(engine: Engine, reviews_dir: Path = REVIEWS_DIR, everything: bool = False) -> list[dict]:
    """Load the downloads into the database, skipping runs already imported unless `everything`."""
    results = []
    with engine.begin() as connection:
        done = set() if everything else database.imported_runs(connection)
        for reviews_file in sorted(reviews_dir.glob("reviews_*.json")):
            run_file = reviews_file.with_name(reviews_file.name.replace("reviews_", "run_"))
            run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
            if run.get("run_id") in done:
                continue
            if run:
                database.save_run(connection, run)
            items = json.loads(reviews_file.read_text(encoding="utf-8"))
            new = database.save_reviews(connection, items, run.get("run_id"))
            results.append({"file": reviews_file.name, "reviews": len(items), "new": new})
    return results


def classify_pending(engine: Engine, model_dir: Path = DEFAULT_MODEL_DIR) -> dict:
    """Classify the Spanish texts that the model has not seen yet."""
    model = SentimentModel(model_dir)
    with engine.begin() as connection:
        pending = database.reviews_to_predict(connection, model_dir.name)
        if not pending:
            return {"classified": 0, "good": 0, "bad": 0}
        probabilities = model.predict_proba([row.text for row in pending])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = [{"review_id": row.review_id, "model": model_dir.name, "probability": probability,
                 "label": "Good" if probability >= model.threshold else "Bad", "threshold": model.threshold,
                 "predicted_at": now}
                for row, probability in zip(pending, probabilities) if probability is not None]
        database.save_predictions(connection, rows)
    good = sum(row["label"] == "Good" for row in rows)
    return {"classified": len(rows), "good": good, "bad": len(rows) - good}


def collect(engine: Engine, max_reviews: int, place_url: str | None = None, place_id: str | None = None,
            since: str | None = None, token: str | None = None, on_progress=print) -> dict:
    """Download, store, import and classify the newest reviews of a place, by URL or Google place id.

    The run's charge is capped at the estimated cost of `max_reviews` plus a small margin."""
    client = ApifyReviews(token)
    max_charge = round(estimated_cost_usd(max_reviews) * 1.05 + 0.01, 4)
    run_id = client.start(max_reviews, max_charge, place_url=place_url, place_id=place_id, since=since)["id"]
    on_progress(f"Apify run {run_id} started (up to {max_reviews} reviews, at most ${max_charge})")
    run = client.fetch(client.wait(run_id, on_progress))
    summary = save_download(run, place_id or place_url, since)
    import_downloads(engine)
    summary["classified"] = classify_pending(engine)["classified"]
    on_progress(f"{summary['reviews']} reviews downloaded for ${summary['cost_usd']}, "
                f"{summary['classified']} classified")
    return summary


def update_place(engine: Engine, place_id: str, max_reviews: int, token: str | None = None,
                 on_progress=print) -> dict:
    """Download only the reviews published since the newest one stored for the place (manual update)."""
    with engine.connect() as connection:
        newest = database.last_published(connection, place_id)
    since = newest[:10] if newest else None
    return collect(engine, max_reviews, place_id=place_id, since=since, token=token, on_progress=on_progress)
