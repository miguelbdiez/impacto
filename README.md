# impacto

**What do people think of a business?** impacto collects the public Google reviews of a business, classifies each one
as good or bad with a text classification model, and shows the results in a dashboard: how opinions evolve, whether
the model agrees with the stars, and what bad and good reviews talk about.

> Portfolio project: machine learning with [Neural Designer](https://www.neuraldesigner.com) and
> [OpenNN](https://github.com/Artelnics/opennn), data analysis, a Streamlit app and a Power BI dashboard.

## How it works

```
Google Maps reviews ──Apify──▶ JSON (data/reviews) ──▶ database ──▶ OpenNN model ──▶ Streamlit app
   (free plan, no reviewer data)                    (SQLite / PostgreSQL)  (good / bad)   └─▶ Power BI
```

- **Model:** trained in the Neural Designer desktop application on 80,000 Spanish Amazon reviews and run with a small
  OpenNN program (6.6 MB instead of the full Neural Designer engine). 88.5% accuracy on held-out reviews and 87.1%
  agreement with the stars on 2,796 real reviews of a department store.
- **App:** a card per business, a dialog to create the dashboard of a new one (search, number of reviews, cost) and,
  for each business, the evolution of good and bad reviews, the model against the stars, the most distinctive words
  and examples. Updates are manual.

## Run it with Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env            # add your Apify token (free account) to download reviews
docker compose up --build
```

The app opens at http://localhost:8501 and PostgreSQL listens on `localhost:5432` for Power BI
([docs/power-bi.md](docs/power-bi.md)); both only accept connections from your own computer. Downloads already in
`data/reviews` are imported on start. The first build compiles OpenNN and takes a few minutes; with plenty of memory
for Docker it can use more parallel jobs: `docker compose build --build-arg BUILD_JOBS=8`.

## Run it without Docker

Requires [uv](https://docs.astral.sh/uv/), and CMake with a C++20 compiler to build the OpenNN predictor once
([docs/inference.md](docs/inference.md)).

```bash
uv sync
uv run playwright install chromium     # for the business search
uv run streamlit run app/streamlit_app.py
```

Without `DATABASE_URL` the data goes to a local SQLite file (`data/impacto.db`).

## Command line

```bash
uv run scraping/download_reviews.py --max-reviews 50      # download reviews of a place with Apify
uv run pipeline/import_reviews.py                         # load downloads into the database
uv run pipeline/predict_reviews.py                        # classify the new Spanish texts
uv run pipeline/update_reviews.py --max-reviews 100       # manual update of every business
uv run pipeline/delete_place.py <place id>                # delete a business and its downloads
uv run --group analysis pipeline/summary.py               # figures of the model on the real reviews
```

## Training data

```bash
uv sync --group analysis
uv run training/download_dataset.py
uv run training/prepare_dataset.py --per-class 40000 --output-dir data/processed_40k
uv run --group analysis training/baseline.py --train data/processed_40k/reviews_es_train.csv
```

The training data and the Neural Designer project are not included in the repository (licence); the documentation
explains how to rebuild them.

## Documentation

- [Decision log](docs/decision-log.md): every design decision and why it was taken
- [Training dataset](docs/dataset.md): source, licence, processing steps and checksums
- [Neural Designer project](docs/neural-designer.md): configuration and how to inspect a saved project
- [Inference with OpenNN](docs/inference.md): export the model, build the predictor and check it
- [Model C](models/model_c/README.md): the published model, its results and terms of use
- [Power BI](docs/power-bi.md): connect to the database and build the report

## Licence

impacto is free software released under the [GNU Affero General Public License v3.0](LICENSE) (`AGPL-3.0-only`),
the same licence as [OpenNN](https://github.com/Artelnics/opennn), which it uses for inference.

The datasets are not covered by this licence and are not included in the repository: each one keeps its own terms
(see [docs/dataset.md](docs/dataset.md)). The published model is derived from the Amazon reviews corpus and may only
be used for non-commercial purposes.
