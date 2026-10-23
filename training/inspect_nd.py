"""Inspect a Neural Designer project (.nd) without opening the application.

A .nd file is an HDF5 container with the model configuration (.ndm, JSON), the report with the
results (.ndo, JSON), the network definition and its parameters. This script prints the current
configuration, to check that the saved project matches the intended one, and every training run
stored in the report. Only the parameters of the last trained network are kept in the project.

Usage:
    uv run --group analysis training/inspect_nd.py impacto.nd [--results training/results/runs.json]
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


# Report tables separate rows with new lines and cells with backslashes
def cells(text: str) -> list[str]:
    return text.split("\\")


def table(subtasks: list[dict], title: str) -> dict:
    found = next(subtask for subtask in subtasks if subtask.get("Title") == title)
    names = cells(found["ColumnNames"]) if found.get("RowNames") in ("", None) else cells(found["RowNames"])
    values = cells(found["Data"]) if "\n" not in found["Data"] else found["Data"].split("\n")
    return dict(zip(names, values))


def confusion_matrix(subtasks: list[dict], labels: list[str]) -> tuple[list[str], list[list[int]]]:
    """Confusion matrix of the report (rows actual, columns predicted) and the label of each row.

    Multi-class tables follow the label order. Binary tables put the positive class first
    ("Actual positive", "Actual negative"), and the positive class is the second label."""
    found = next(subtask for subtask in subtasks if subtask.get("Title") == "Confusion table")
    names = [name.removeprefix("Actual ") for name in cells(found["RowNames"])][:len(labels)]
    order = [{"positive": labels[-1], "negative": labels[0]}.get(name, name) for name in names]
    rows = [cells(row) for row in found["Data"].split("\n")][:len(labels)]
    return order, [[int(cell.split(" ")[0]) for cell in row[:len(labels)]] for row in rows]


def confusion(subtasks: list[dict], labels: list[str]) -> dict:
    labels, matrix = confusion_matrix(subtasks, labels)
    correct = sum(matrix[i][i] for i in range(len(labels)))

    return {
        "testing_samples": sum(map(sum, matrix)),
        "testing_accuracy": round(correct / sum(map(sum, matrix)), 4),
        "recall": {label: round(matrix[i][i] / sum(matrix[i]), 4) for i, label in enumerate(labels)},
        "precision": {label: round(matrix[i][i] / sum(row[i] for row in matrix), 4) for i, label in enumerate(labels)},
        "confusion_matrix_testing": {"labels": labels, "rows_actual_columns_predicted": matrix},
    }


def training_runs(report: dict, labels: list[str]) -> list[dict]:
    """Every training in the report, with the data and network reported before it and the testing
    analysis computed after it."""
    runs, data, network = [], None, None

    for task in report["Tasks"]:
        subtasks = task.get("Subtasks", [])
        if task["Name"] == "Report dataset":
            data = table(subtasks, "Corpus information")
        elif task["Name"] == "Report neural network":
            graph = next(subtask for subtask in subtasks if subtask["Type"] == "NeuralNetworkGraph")
            network = [f"{name} [{shape}]" for name, shape in zip(cells(graph["LayersName"]), cells(graph["LayerShapes"]))]
            # The network may be reported after training it
            if runs and runs[-1]["network"] is None:
                runs[-1]["network"] = network
        elif task["Name"] == "Perform training":
            chart = next(subtask for subtask in subtasks if subtask["Type"] == "DoubleLineChart")
            validation = [float(value) for value in cells(chart["Y2Data"])]
            runs.append({
                "data": data,
                "network": network,
                "summary": table(subtasks, "Adaptive moment estimation results"),
                "best_validation_epoch": validation.index(min(validation)) + 1,
                "history": {"training_error": [float(value) for value in cells(chart["Y1Data"])],
                            "validation_error": validation},
            })
        elif task["Name"] == "Calculate ROC curve" and runs:
            runs[-1]["area_under_curve"] = float(next(iter(table(subtasks, "Area under curve").values())))
        elif task["Name"] == "Calculate confusion" and runs:
            runs[-1].update(confusion(subtasks, labels))

    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--results", type=Path, help="save the configuration and every run to this JSON file")
    args = parser.parse_args()

    container = read_container(args.project)
    config = configuration(container["model"])
    vocabulary = container["model"]["Dataset"]["InputTokenizer"]["Vocabulary"]
    runs = training_runs(container["report"], config["labels"])

    print(json.dumps(config, indent=2))
    print("Most frequent tokens:", vocabulary[len(config["reserved_tokens"]):][:30])

    for number, run in enumerate(runs, start=1):
        summary = run["summary"]
        print(f"\nRun {number}: data {run['data']}")
        print(f"  network: {' -> '.join(run['network'] or [])}")
        print(f"  {summary.get('Epochs number')} epochs (best {run['best_validation_epoch']}), "
              f"stopped by '{summary.get('Stopping criterion')}' in {summary.get('Elapsed time')}, "
              f"validation error {summary.get('Validation error')}")
        if "testing_accuracy" in run:
            recall = ", ".join(f"{label} {value:.1%}" for label, value in run["recall"].items())
            print(f"  testing accuracy {run['testing_accuracy']:.1%} on {run['testing_samples']} samples, "
                  f"recall {recall}, AUC {run.get('area_under_curve')}")

    if args.results:
        args.results.write_text(json.dumps({"configuration": config, "runs": runs}, indent=2))
        print(f"\nSaved {args.results}")


if __name__ == "__main__":
    main()
