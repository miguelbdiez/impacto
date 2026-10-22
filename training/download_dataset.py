"""Download the Spanish subset of the Multilingual Amazon Reviews Corpus.

The data is not redistributed in this repository (see docs/dataset.md for the licence).
This script fetches it from a Hugging Face Hub mirror that keeps the original files and
columns (review title, product category, anonymised product and reviewer ids).

Usage:
    uv run training/download_dataset.py
"""

import argparse
import urllib.request
from pathlib import Path

REPOSITORY = "buruzaemon/amazon_reviews_multi"
REVISION = "486fbd96a972291f6d7b4cad9d88088c5983244c"  # pinned commit, for reproducibility
BASE_URL = f"https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/es"
SPLITS = ("train", "validation", "test")


def download(split: str, output_dir: Path, force: bool) -> Path:
    destination = output_dir / f"{split}.jsonl.gz"

    if destination.exists() and not force:
        print(f"{destination} already exists, skipping (use --force to download it again)")
        return destination

    url = f"{BASE_URL}/{split}.jsonl.gz"
    print(f"Downloading {url}")

    # Download to a temporary name so an interrupted download never looks complete
    partial = destination.with_suffix(".part")
    urllib.request.urlretrieve(url, partial)
    partial.replace(destination)

    print(f"  -> {destination} ({destination.stat().st_size / 1e6:.1f} MB)")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--force", action="store_true", help="download again even if the files exist")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for split in SPLITS:
        download(split, args.output_dir, args.force)


if __name__ == "__main__":
    main()
