"""Sentiment model trained in Neural Designer, run with OpenNN.

Predictions come from a small C++ program linked with OpenNN (inference/predict.cpp), which loads
the model exported by training/export_model.py. Texts are normalised here with the same function
used to build the training data (D-008), so training and inference see the same tokens.
"""

import json
import os
import subprocess
from pathlib import Path

from impacto.text import normalize_text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = ROOT / "models" / "model_c"
# Visual Studio builds into a Release subfolder; single-configuration generators (Linux) do not
EXECUTABLE_CANDIDATES = [
    ROOT / "build" / "inference" / "Release" / "impacto_predict.exe",
    ROOT / "build" / "inference" / "impacto_predict",
]


def find_executable() -> Path:
    if "IMPACTO_PREDICT" in os.environ:
        return Path(os.environ["IMPACTO_PREDICT"])
    for candidate in EXECUTABLE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("impacto_predict not found: build inference/ (see docs/inference.md) "
                            "or set IMPACTO_PREDICT")


class SentimentModel:
    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR, executable: Path | None = None):
        self.model_dir = Path(model_dir)
        self.executable = executable or find_executable()
        info = json.loads((self.model_dir / "model_info.json").read_text())
        self.sequence_length = info["sequence_length"]
        self.labels = info["labels"]
        self.threshold = info.get("decision_threshold", 0.5)

    def predict_proba(self, texts: list[str]) -> list[float | None]:
        """Probability that each text is a good review, or None for texts without words (e.g. a review
        with stars only), which the model cannot judge."""
        # normalize_text also removes line breaks, so each text travels as exactly one line
        normalized = [normalize_text(text) for text in texts]
        indices = [i for i, text in enumerate(normalized) if text]
        if not indices:
            return [None] * len(texts)

        lines = "".join(normalized[i] + "\n" for i in indices)
        result = subprocess.run([str(self.executable), str(self.model_dir), str(self.sequence_length)],
                                input=lines, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"impacto_predict failed: {result.stderr.strip()}")

        values = [float(value) for value in result.stdout.split()]
        if len(values) != len(indices):
            raise RuntimeError(f"impacto_predict returned {len(values)} values for {len(indices)} texts")

        probabilities: list[float | None] = [None] * len(texts)
        for i, value in zip(indices, values):
            probabilities[i] = value
        return probabilities

    def predict(self, texts: list[str], threshold: float | None = None) -> list[str | None]:
        """'Good' or 'Bad' for each text (None if it has no words), using the model's decision
        threshold unless one is given."""
        threshold = self.threshold if threshold is None else threshold
        return [None if probability is None else "Good" if probability >= threshold else "Bad"
                for probability in self.predict_proba(texts)]
