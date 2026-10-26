"""Classify the reviews in the database with the OpenNN model (decisions D-015, D-018).

Only reviews with text in Spanish are classified, and only once per model: running it again only
processes the new ones.

Usage:
    uv run pipeline/predict_reviews.py [--model-dir models/model_c]
"""

import argparse
from pathlib import Path

from impacto import database
from impacto.model import DEFAULT_MODEL_DIR
from impacto.pipeline import classify_pending


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    result = classify_pending(database.connect(), args.model_dir)
    print(f"{result['classified']} reviews classified with {args.model_dir.name}: "
          f"{result['good']} good, {result['bad']} bad")


if __name__ == "__main__":
    main()
