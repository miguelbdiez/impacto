"""Domain shift: how well does a model trained on Amazon product reviews work on hospitality reviews?

Trains the TF-IDF + logistic regression baseline and tests it on two public Spanish datasets
(MIT licence) from the hospitality sector:
  - Punta Cana hotel reviews: real reviews, Spanish ones only, split 70% training / 30% testing.
  - HorecaReviews-ES: synthetic reviews of bars, cafés and restaurants written in different styles
    (enthusiastic, critical, sarcastic...).
Labels follow D-002: 1-2 stars -> Bad, 4-5 stars -> Good, 3 stars dropped. The datasets are
downloaded to data/external/.

Usage:
    uv run --group analysis training/domain_shift.py [--train data/processed/reviews_es_train.csv]
"""

import argparse
import urllib.request
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, recall_score

from impacto.text import normalize_text

HUB = "https://huggingface.co/datasets"
HOTELS_URL = f"{HUB}/beltrewilton/punta-cana-spanish-reviews/resolve/e4404ae54c02c1a53b9b3a5822b1fc2860a05fb1/punta_cana.csv"
HORECA_URL = f"{HUB}/mrcsgh/horeca-spanish-reviews/resolve/4ee2a31541ee87cd296f422c4932158b24cb2f50/dataset.txt"
SENTIMENT_BY_STARS = {1: "Bad", 2: "Bad", 4: "Good", 5: "Good"}

# The hotel dataset mixes Spanish and English reviews: keep those with clearly more Spanish function words
SPANISH_WORDS = {"el", "la", "de", "que", "y", "en", "los", "las", "muy", "es", "con", "para", "por", "pero", "una"}
ENGLISH_WORDS = {"the", "and", "was", "is", "with", "for", "very", "we", "our", "but", "were", "of", "to"}


def download(url: str, destination: Path) -> Path:
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, destination)
    return destination


def is_spanish(text: str) -> bool:
    words = text.lower().split()
    return sum(word in SPANISH_WORDS for word in words) > 2 * sum(word in ENGLISH_WORDS for word in words)


def labelled(reviews: pd.DataFrame, text: str, stars: str, **extra: str) -> pd.DataFrame:
    reviews = reviews[reviews[stars].isin(SENTIMENT_BY_STARS.keys())]
    return pd.DataFrame({"text": reviews[text].map(normalize_text),
                         "sentiment": reviews[stars].map(SENTIMENT_BY_STARS),
                         **{name: reviews[column] for name, column in extra.items()}})


def load_amazon(path: Path, seed: int) -> pd.DataFrame:
    # Same 60% training part as training/baseline.py
    reviews = pd.read_csv(path, sep="\t", quoting=3, dtype=str, keep_default_na=False).sample(frac=1, random_state=seed)
    return reviews.iloc[:int(0.6 * len(reviews))].rename(columns={"review_body": "text"})[["text", "sentiment"]]


def evaluate(train: pd.DataFrame, tests: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    # Balanced class weights: the hotel reviews are 93% positive
    model = LogisticRegression(C=2.0, max_iter=2000, class_weight="balanced")
    model.fit(vectorizer.fit_transform(train["text"]), train["sentiment"])
    return {name: pd.Series(model.predict(vectorizer.transform(test["text"])), index=test.index)
            for name, test in tests.items()}


def summary(actual: pd.Series, predicted: pd.Series) -> str:
    bad, good = recall_score(actual, predicted, labels=["Bad", "Good"], average=None)
    return f"{balanced_accuracy_score(actual, predicted):.1%} (recall bad {bad:.0%} / good {good:.0%})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", type=Path, default=Path("data/processed/reviews_es_train.csv"))
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    hotels = pd.read_csv(download(HOTELS_URL, args.external_dir / "punta_cana.csv"))
    hotels = labelled(hotels[hotels["review_text"].astype(str).map(is_spanish)], "review_text", "rating")
    hotels = hotels.sample(frac=1, random_state=args.seed)
    hotels_train, hotels_test = hotels.iloc[:int(0.7 * len(hotels))], hotels.iloc[int(0.7 * len(hotels)):]
    horeca = pd.read_csv(download(HORECA_URL, args.external_dir / "horeca.txt"), sep="\t")
    horeca = labelled(horeca, "texto", "estrellas", style="estilo")
    amazon = load_amazon(args.train, args.seed)

    print(f"Hotels: {hotels['sentiment'].value_counts().to_dict()}, testing on {len(hotels_test)}")
    print(f"Bars and restaurants (synthetic): {horeca['sentiment'].value_counts().to_dict()}")

    tests = {"hotels": hotels_test, "bars": horeca}
    experiments = {
        f"Amazon ({len(amazon)})": amazon,
        f"Hotels ({len(hotels_train)})": hotels_train,
        f"Amazon + hotels ({len(amazon) + len(hotels_train)})": pd.concat([amazon, hotels_train]),
    }
    for name, train in experiments.items():
        predictions = evaluate(train, tests)
        print(f"\nTrained on {name}")
        for test_name, test in tests.items():
            print(f"  {test_name:<7} {summary(test['sentiment'], predictions[test_name])}")
        correct = (predictions["bars"] == horeca["sentiment"]).groupby(horeca["style"]).mean().sort_values()
        print("  bars by style: " + ", ".join(f"{style} {value:.0%}" for style, value in correct.items()))


if __name__ == "__main__":
    main()
