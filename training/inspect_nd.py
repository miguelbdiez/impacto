"""Inspect a Neural Designer project (.nd) without opening the application.

A .nd file is an HDF5 container with the model configuration (.ndm, JSON), the report with the
results (.ndo, JSON), the network definition and its parameters. This script prints what is needed
to check that the saved project matches the intended configuration, and can save the results of the
last training as JSON (training/results/).

Usage:
    uv run --group analysis training/inspect_nd.py impacto.nd [--results training/results/modelN.json]
"""

import argparse
import json
from pathlib import Path

import h5py

LAYER_DETAILS = ("OutputDimensions", "VocabularySize", "HeadsNumber", "PoolingMethod", "Activation")


def read_container(path: Path) -> dict:
    with h5py.File(path, "r") as container:
        files = {name: dataset[()].tobytes() for name, dataset in container["files"].items()}

    def document(suffix: str) -> dict:
        return json.loads(next(content for name, content in files.items() if name.endswith(suffix)))

    return {"model": document(".ndm"), "report": document(".ndo")}


def configuration(model: dict) -> dict:
    dataset = model["Dataset"]
    source = dataset["DataSource"]
    tokenizer = dataset["InputTokenizer"]
    loss = model["Training"]["Loss"]
    adam = model["Training"]["Optimizer"]["Adam"]
    layers = []
    for item in model["Network"]["Layers"]["Items"]:
        (kind, layer), = item.items()
        layers.append({"layer": kind, **{key: layer[key] for key in LAYER_DETAILS if key in layer}})

    return {
        "data_file": source["Path"],
        "column_roles": {column["Name"]: column["Role"] for column in source["TextColumns"]},
        "sequence_length": dataset["InputSequenceLength"],
        "vocabulary_size": len(tokenizer["Vocabulary"]),
        "minimum_token_frequency": source["MinimumTokenFrequency"],
        "reserved_tokens": tokenizer["ReservedTokens"],
        "labels": dataset["Labels"],
        "network": layers,
        "training": {
            "loss": loss["Error"],
            "regularization": f"{loss['Regularization']['Type']} ({loss['Regularization']['RegularizationWeight']})",
            "learning_rate": adam["LearningRate"],
            "batch_size": adam["BatchSize"],
            "maximum_epochs": adam["MaximumEpochsNumber"],
            "maximum_validation_failures": adam["MaximumValidationFailures"],
        },
        "trained": model["ModelMetaData"]["Trained"],
        "last_change": model["ModelMetaData"]["DateStatus"],
    }


def last_results(report: dict, labels: list[str]) -> dict | None:
    """Results of the last training and confusion matrix stored in the report, if any."""
    trainings = [task for task in report["Tasks"] if task["Name"] == "Perform training"]
    confusions = [task for task in report["Tasks"] if task["Name"] == "Calculate confusion"]
    if not trainings or not confusions:
        return None

    subtasks = trainings[-1]["Subtasks"]
    chart = next(subtask for subtask in subtasks if subtask["Type"] == "DoubleLineChart")
    summary = next(subtask for subtask in subtasks if subtask.get("Title", "").endswith("results"))
    table = next(subtask for subtask in confusions[-1]["Subtasks"] if subtask["Type"] == "Table")

    # Report tables separate rows with new lines and cells with backslashes
    validation = [float(value) for value in chart["Y2Data"].split("\\")]
    rows = [row.split("\\") for row in table["Data"].split("\n")][:len(labels)]
    matrix = [[int(cell.split(" ")[0]) for cell in row[:len(labels)]] for row in rows]
    correct = sum(matrix[i][i] for i in range(len(labels)))

    return {
        "summary": dict(zip(summary["RowNames"].split("\\"), summary["Data"].split("\n"))),
        "best_validation_epoch": validation.index(min(validation)),
        "testing_accuracy": round(correct / sum(map(sum, matrix)), 4),
        "recall": {label: round(matrix[i][i] / sum(matrix[i]), 4) for i, label in enumerate(labels)},
        "precision": {label: round(matrix[i][i] / sum(row[i] for row in matrix), 4) for i, label in enumerate(labels)},
        "confusion_matrix_testing": {"labels": labels, "rows_actual_columns_predicted": matrix},
        "history": {
            "training_error": [float(value) for value in chart["Y1Data"].split("\\")],
            "validation_error": validation,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--results", type=Path, help="save configuration and last results to this JSON file")
    args = parser.parse_args()

    container = read_container(args.project)
    config = configuration(container["model"])
    vocabulary = container["model"]["Dataset"]["InputTokenizer"]["Vocabulary"]
    results = last_results(container["report"], config["labels"])

    print(json.dumps(config, indent=2))
    print("Most frequent tokens:", vocabulary[len(config["reserved_tokens"]):][:30])
    if results:
        print(json.dumps({key: value for key, value in results.items() if key != "history"}, indent=2))

    if args.results:
        args.results.write_text(json.dumps({"configuration": config, "results": results}, indent=2))
        print(f"Saved {args.results}")


if __name__ == "__main__":
    main()
