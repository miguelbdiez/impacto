"""Reference baseline: TF-IDF + logistic regression on the same training file.

Gives a lower bound that any neural network trained in Neural Designer should beat. It uses the same
proportions as Neural Designer (60% training, 20% testing of the file), and also reports the
hold-out set.

Usage:
    uv run --group analysis training/baseline.py [--train data/processed/reviews_es_train.csv]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", quoting=3, dtype=str, keep_default_na=False)


def report(name: str, actual: pd.Series, predicted: np.ndarray) -> None:
    labels = sorted(actual.unique())
    matrix = confusion_matrix(actual, predicted, labels=labels)
    recall = matrix.diagonal() / matrix.sum(axis=1)
    recalls = ", ".join(f"{label} {value:.1%}" for label, value in zip(labels, recall))

    print(f"{name}: {len(actual)} reviews, "
          f"balanced accuracy {balanced_accuracy_score(actual, predicted):.1%}, recall {recalls}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", type=Path, default=Path("data/processed/reviews_es_train.csv"))
    parser.add_argument("--holdout", type=Path, default=Path("data/processed/reviews_es_holdout.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    reviews = read(args.train).sample(frac=1, random_state=args.seed)
    training = reviews.iloc[:int(0.6 * len(reviews))]
    testing = reviews.iloc[int(0.8 * len(reviews)):]
    holdout = read(args.holdout)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    model = LogisticRegression(C=2.0, max_iter=2000)
    model.fit(vectorizer.fit_transform(training["review_body"]), training["sentiment"])

    print(f"TF-IDF (1-2 grams) + logistic regression, trained on {len(training)} reviews")
    for name, subset in (("testing", testing), ("hold-out", holdout)):
        report(name, subset["sentiment"], model.predict(vectorizer.transform(subset["review_body"])))


if __name__ == "__main__":
    main()
