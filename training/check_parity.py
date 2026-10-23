"""Check that OpenNN reproduces Neural Designer on the testing subset of the project.

The project (.nd) stores which samples were used for testing, and its report holds the area under
the ROC curve and the confusion matrix Neural Designer computed on them. This script predicts the
same samples with the exported model and OpenNN and compares:
  - the area under the ROC curve, which does not depend on the decision threshold;
  - the confusion matrix, both at a 0.5 threshold and at the threshold that predicts as many
    positives as Neural Designer did.

Usage:
    uv run --group analysis training/check_parity.py models/impacto_model_c.nd data/processed_40k/reviews_es_train.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from impacto.model import SentimentModel
from inspect_nd import confusion_matrix, read_container, training_runs

TESTING = "2"  # SampleRole::Testing in OpenNN


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--model-dir", type=Path, default=Path("models/model_c"))
    args = parser.parse_args()

    container = read_container(args.project)
    dataset = container["model"]["Dataset"]
    samples = dataset["Samples"]
    roles = pd.Series(samples["SampleRoles"].split(), index=samples["SamplesId"].split("\t"))
    reviews = pd.read_csv(args.data_file, sep="\t", quoting=3, dtype=str, keep_default_na=False)
    testing = reviews.set_index("review_id").loc[roles[roles == TESTING].index]

    probability = np.array(SentimentModel(args.model_dir).predict_proba(testing["review_body"].tolist()))
    positive = (testing["sentiment"] == "Good").to_numpy()

    # Neural Designer's matrix, reordered as [positive, negative]
    confusion_task = [task for task in container["report"]["Tasks"] if task["Name"] == "Calculate confusion"][-1]
    order, matrix = confusion_matrix(confusion_task["Subtasks"], dataset["Labels"])
    index = [order.index("good"), order.index("bad")]
    neural_designer = np.array(matrix)[np.ix_(index, index)]
    predicted_positives = int(neural_designer[:, 0].sum())

    def ours(threshold: float) -> np.ndarray:
        predicted = probability >= threshold
        return np.array([[(positive & predicted).sum(), (positive & ~predicted).sum()],
                         [(~positive & predicted).sum(), (~positive & ~predicted).sum()]])

    ranked = np.sort(probability)[::-1]
    equivalent = float((ranked[predicted_positives - 1] + ranked[predicted_positives]) / 2)

    print(f"Testing samples: {len(testing)}")
    print(f"Area under ROC curve: OpenNN {roc_auc_score(positive, probability):.4f}, "
          f"Neural Designer {training_runs(container['report'], dataset['Labels'])[-1].get('area_under_curve')}")
    print("Confusion matrices, rows actual [good, bad], columns predicted [good, bad]:")
    print(f"  Neural Designer:                     {neural_designer.tolist()}")
    for name, threshold in (("0.5", 0.5), (f"{equivalent:.4f} (same positives)", equivalent)):
        matrix = ours(threshold)
        print(f"  OpenNN, threshold {name:<18} {matrix.tolist()}  "
              f"largest cell difference {np.abs(matrix - neural_designer).max()}")


if __name__ == "__main__":
    main()
