"""Export the trained model of a Neural Designer project (.nd) for inference with OpenNN.

Neural Designer stores the network and its parameters in OpenNN's own formats, and the vocabulary in
the project configuration (.ndm). This script copies them out of the .nd container:

  model.json       network definition (OpenNN JSON)
  model.bin        trained parameters (OpenNN binary; OpenNN loads it from next to model.json)
  vocabulary.txt   one token per line, the line number is the token id
  model_info.json  sequence length, class labels and decision threshold, read by the Python wrapper

Usage:
    uv run --group analysis training/export_model.py models/impacto_model_c.nd models/model_c [--threshold 0.5]
"""

import argparse
import json
from pathlib import Path

import h5py


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="probability of the positive class from which a review is classified as positive")
    args = parser.parse_args()

    with h5py.File(args.project, "r") as container:
        files = {name: dataset[()].tobytes() for name, dataset in container["files"].items()}

    def content(suffix: str) -> bytes:
        return next(data for name, data in files.items() if name.endswith(suffix))

    dataset = json.loads(content(".ndm"))["Dataset"]
    vocabulary = dataset["InputTokenizer"]["Vocabulary"]
    # Tokens are runs of ASCII letters and digits or single punctuation marks, so one per line is safe
    assert all(token and "\n" not in token for token in vocabulary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "model.json").write_bytes(content("_Network.json"))
    (args.output_dir / "model.bin").write_bytes(content("_Params.bin"))
    (args.output_dir / "vocabulary.txt").write_text("\n".join(vocabulary) + "\n", encoding="utf-8", newline="\n")
    (args.output_dir / "model_info.json").write_text(json.dumps({
        "source": args.project.name,
        "sequence_length": dataset["InputSequenceLength"],
        "labels": dataset["Labels"],
        "decision_threshold": args.threshold,
        "reserved_tokens": dataset["InputTokenizer"]["ReservedTokens"],
        "vocabulary_size": len(vocabulary),
    }, indent=2))

    print(f"Exported {args.project} to {args.output_dir}: vocabulary {len(vocabulary)}, "
          f"sequence length {dataset['InputSequenceLength']}, labels {dataset['Labels']}")


if __name__ == "__main__":
    main()
