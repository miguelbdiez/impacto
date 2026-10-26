"""Summary of the reviews in the database and of the model on them (decision D-019).

The stars give a free label for every review with text: 1-2 stars should be 'Bad' and 4-5 stars
'Good'. Comparing them with the model's predictions measures how well the model, trained on Amazon
product reviews, works on the real business (D-011). 3-star reviews are left out of that comparison.

Usage:
    uv run --group analysis pipeline/summary.py [--model model_c]
"""

import argparse

import pandas as pd
from sklearn.metrics import roc_auc_score
from sqlalchemy import text

from impacto import database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=database.MODEL)
    args = parser.parse_args()

    with database.connect().connect() as connection:
        reviews = pd.read_sql(text("""SELECT r.*, p.probability, p.label FROM reviews r
                                      LEFT JOIN predictions p ON p.review_id = r.review_id AND p.model = :model"""),
                              connection, params={"model": args.model})
    reviews["year"] = reviews["published_at"].str[:4]
    classified = reviews[reviews["label"].notna()]

    print(f"{len(reviews)} reviews from {reviews['published_at'].min()[:10]} to {reviews['published_at'].max()[:10]}, "
          f"mean {reviews['stars'].mean():.2f} stars")
    print(f"With text: {reviews['text'].notna().sum()}, classified (Spanish): {len(classified)}, "
          f"predicted good: {(classified['label'] == 'Good').mean():.1%}")

    polar = classified[classified["stars"] != 3]
    truth = polar["stars"].map(lambda stars: "Good" if stars >= 4 else "Bad")
    correct = truth == polar["label"]
    recall = correct.groupby(truth).mean()
    print(f"\nModel vs stars ({len(polar)} reviews with 1-2 or 4-5 stars): agreement {correct.mean():.1%}, "
          f"recall bad {recall['Bad']:.1%} / good {recall['Good']:.1%}, "
          f"AUC {roc_auc_score(truth == 'Good', polar['probability']):.3f}")
    print("Share predicted good by stars:",
          {stars: f"{share:.0%}" for stars, share in
           classified.groupby("stars")["label"].apply(lambda labels: (labels == "Good").mean()).items()})

    by_year = reviews.groupby("year").agg(
        reviews=("review_id", "size"),
        mean_stars=("stars", "mean"),
        with_text_pct=("text", lambda texts: texts.notna().mean() * 100),
        stars_1_2_pct=("stars", lambda stars: (stars <= 2).mean() * 100))
    by_year["classified"] = classified.groupby("year").size()
    by_year["predicted_bad_pct"] = classified.groupby("year")["label"].apply(lambda labels: (labels == "Bad").mean() * 100)
    print(f"\n{by_year.round(1).to_string()}")


if __name__ == "__main__":
    main()
