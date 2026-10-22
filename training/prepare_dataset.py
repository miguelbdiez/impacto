"""Build the Neural Designer training file from the raw Amazon reviews.

Steps (explained in docs/dataset.md):
  1. Normalise the text to ASCII (same function used at inference) so the file parses as plain
     tab-separated values and the OpenNN tokenizer keeps every word whole.
  2. Drop empty and duplicated reviews, and training reviews that also appear in the hold-out set.
  3. Label from the stars: 1-2 -> Bad, 3 -> Neutral, 4-5 -> Good.
  4. Draw a balanced random sample for training. The official test split is kept apart as hold-out.

Outputs (in data/processed/):
  reviews_es_train.csv    file to import in Neural Designer
  reviews_es_holdout.csv  never seen during training, used later to test the deployed model
  stats.json              figures reported in docs/dataset.md

Usage:
    uv run training/prepare_dataset.py [--per-class 10000] [--seed 42]
"""

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from impacto.text import normalize_text

# Identifier first and target last: the default column roles in Neural Designer / OpenNN
COLUMNS = ["review_id", "product_id", "reviewer_id", "product_category", "stars",
           "review_title", "review_body", "sentiment"]
TEXT_COLUMNS = ["review_title", "review_body"]
SENTIMENT_BY_STARS = {1: "Bad", 2: "Bad", 3: "Neutral", 4: "Good", 5: "Good"}


def load_split(raw_dir: Path, split: str) -> pd.DataFrame:
    return pd.read_json(raw_dir / f"{split}.jsonl.gz", lines=True, dtype={"stars": int})


def prepare(reviews: pd.DataFrame) -> pd.DataFrame:
    reviews = reviews.assign(**{column: reviews[column].map(normalize_text) for column in TEXT_COLUMNS})
    reviews = reviews[reviews["review_body"] != ""]
    reviews = reviews.drop_duplicates("review_body")

    return reviews.assign(sentiment=reviews["stars"].map(SENTIMENT_BY_STARS))


def balanced_sample(reviews: pd.DataFrame, per_class: int, seed: int) -> pd.DataFrame:
    if per_class:
        available = reviews["sentiment"].value_counts().min()
        if per_class > available:
            raise SystemExit(f"--per-class {per_class} is larger than the smallest class ({available})")
        reviews = reviews.groupby("sentiment").sample(n=per_class, random_state=seed)

    return reviews.sample(frac=1, random_state=seed)


def write_tsv(reviews: pd.DataFrame, path: Path) -> None:
    reviews[COLUMNS].to_csv(path, sep="\t", index=False, encoding="utf-8",
                            quoting=csv.QUOTE_NONE, lineterminator="\n")


def counts(column: pd.Series) -> dict:
    return {str(value): int(count) for value, count in column.value_counts().sort_index().items()}


def describe(reviews: pd.DataFrame) -> dict:
    words = reviews["review_body"].str.split().str.len()

    return {
        "rows": len(reviews),
        "sentiment": counts(reviews["sentiment"]),
        "stars": counts(reviews["stars"]),
        "product_category": counts(reviews["product_category"]),
        "words_per_review": {
            "min": int(words.min()),
            "median": int(words.median()),
            "p95": int(words.quantile(0.95)),
            "max": int(words.max()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--per-class", type=int, default=10_000,
                        help="training reviews per class (0 = use all of them)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    raw = {split: load_split(args.raw_dir, split) for split in ("train", "validation", "test")}

    holdout = prepare(raw["test"])
    pool = prepare(pd.concat([raw["train"], raw["validation"]]))
    pool = pool[~pool["review_body"].isin(holdout["review_body"])]
    train = balanced_sample(pool, args.per_class, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(train, args.output_dir / "reviews_es_train.csv")
    write_tsv(holdout, args.output_dir / "reviews_es_holdout.csv")

    stats = {
        "raw_rows": {split: len(reviews) for split, reviews in raw.items()},
        "training_pool": describe(pool),
        "train": describe(train),
        "holdout": describe(holdout),
        "per_class": args.per_class,
        "seed": args.seed,
    }
    (args.output_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
