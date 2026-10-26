"""Classify the reviews in the database with the OpenNN model (decisions D-015, D-018).

Only reviews with text in Spanish are classified, and only once per model: running it again only
processes the new ones.

Usage:
    uv run pipeline/predict_reviews.py [--model-dir models/model_c] [--database data/impacto.db]
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from impacto.database import DEFAULT_PATH, connect, reviews_to_predict, save_predictions
from impacto.model import SentimentModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-dir", type=Path, default=Path("models/model_c"))
    parser.add_argument("--database", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    model = SentimentModel(args.model_dir)
    name = args.model_dir.name
    connection = connect(args.database)
    pending = reviews_to_predict(connection, name)
    if not pending:
        print(f"No reviews pending for {name}")
        return

    probabilities = model.predict_proba([row["text"] for row in pending])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [{"review_id": row["review_id"], "model": name, "probability": probability,
             "label": "Good" if probability >= model.threshold else "Bad", "threshold": model.threshold,
             "predicted_at": now}
            for row, probability in zip(pending, probabilities) if probability is not None]
    save_predictions(connection, rows)

    good = sum(row["label"] == "Good" for row in rows)
    print(f"{len(rows)} reviews classified with {name} (threshold {model.threshold}): "
          f"{good} good, {len(rows) - good} bad")


if __name__ == "__main__":
    main()
