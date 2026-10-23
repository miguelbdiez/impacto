"""Check the OpenNN predictor on the hold-out set, which neither Neural Designer nor OpenNN has seen.

Reports accuracy and recall per class. With --reference it also compares the probabilities with
the predictions of another source, such as the Neural Designer deploy package, which must give
the same values.

Usage:
    uv run --group analysis training/evaluate_inference.py [--threshold 0.44] [--reference predictions.csv]

The reference CSV needs a 'review_id' column and a 'probability' column (probability of 'good').
"""

import argparse
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from impacto.model import SentimentModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--holdout", type=Path, default=Path("data/processed/reviews_es_holdout.csv"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/model_c"))
    parser.add_argument("--threshold", type=float,
                        help="probability from which a review is 'Good' (default: the model's decision threshold)")
    parser.add_argument("--reference", type=Path, help="CSV with review_id and probability to compare with")
    parser.add_argument("--output", type=Path, help="save review_id, sentiment and probability to this CSV")
    args = parser.parse_args()

    reviews = pd.read_csv(args.holdout, sep="\t", quoting=3, dtype=str, keep_default_na=False)
    model = SentimentModel(args.model_dir)

    start = time.time()
    reviews["probability"] = model.predict_proba(reviews["review_body"].tolist())
    elapsed = time.time() - start
    threshold = model.threshold if args.threshold is None else args.threshold
    reviews["predicted"] = reviews["probability"].map(lambda probability: "Good" if probability >= threshold else "Bad")

    correct = reviews["predicted"] == reviews["sentiment"]
    recall = correct.groupby(reviews["sentiment"]).mean()
    area = roc_auc_score(reviews["sentiment"] == "Good", reviews["probability"])
    print(f"{len(reviews)} hold-out reviews predicted with OpenNN in {elapsed:.1f} s")
    print(f"Threshold {threshold}: accuracy {correct.mean():.1%}, recall "
          + ", ".join(f"{label} {value:.1%}" for label, value in recall.items()) + f", AUC {area:.4f}")

    if args.output:
        reviews[["review_id", "sentiment", "probability"]].to_csv(args.output, index=False)

    if args.reference:
        reference = pd.read_csv(args.reference, dtype={"review_id": str})
        merged = reviews.merge(reference, on="review_id", suffixes=("", "_reference"))
        difference = (merged["probability"] - merged["probability_reference"]).abs()
        print(f"Compared with {args.reference} on {len(merged)} reviews: "
              f"maximum difference {difference.max():.2e}, mean {difference.mean():.2e}")


if __name__ == "__main__":
    main()
