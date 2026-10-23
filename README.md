# impacto

**What do people think of a business?** impacto collects the public reviews of a business, classifies each one as
good or bad with a text classification model, and shows the results in a dashboard that refreshes automatically.

> Work in progress. Portfolio project: machine learning with [Neural Designer](https://www.neuraldesigner.com) and
> [OpenNN](https://github.com/Artelnics/opennn), data analysis, and dashboards with Power BI.

## Pipeline

```
Scraper (Python) -> Database -> Sentiment model (OpenNN) -> Power BI dashboard
                 ^                                                |
                 +----------- scheduler (configurable interval) --+
```

The model is trained in the Neural Designer desktop application and deployed with OpenNN, everything packaged with
Docker.

## Roadmap

- [x] Training dataset: Spanish Amazon reviews ([docs/dataset.md](docs/dataset.md))
- [x] Model training in Neural Designer
- [x] Inference with OpenNN ([docs/inference.md](docs/inference.md))
- [ ] Review scraper and scheduler
- [ ] Database and Power BI dashboard
- [ ] Docker deployment

## Quick start: training data

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group analysis
uv run training/download_dataset.py
uv run training/prepare_dataset.py
uv run --group analysis training/baseline.py    # reference model to compare with
```

This creates `data/processed/reviews_es_train.csv`, ready to import in Neural Designer. The data and the Neural
Designer project are not included in the repository (licence); the documentation explains how to rebuild them.

## Documentation

- [Training dataset](docs/dataset.md): source, licence, processing steps and checksums
- [Neural Designer project](docs/neural-designer.md): configuration and how to inspect a saved project
- [Inference with OpenNN](docs/inference.md): export the model, build the predictor and check it
- [Decision log](docs/decision-log.md): every design decision and why it was taken

## Licence

impacto is free software released under the [GNU Affero General Public License v3.0](LICENSE) (`AGPL-3.0-only`),
the same licence as [OpenNN](https://github.com/Artelnics/opennn), which it uses for inference.

The datasets are not covered by this licence and are not included in the repository: each one keeps its own terms
(see [docs/dataset.md](docs/dataset.md)).
