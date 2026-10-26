# impacto: notes for Claude Code

## Context

- Portfolio project. The goal is a public GitHub repository plus a LinkedIn post (in Spanish) showing an end-to-end
  machine learning project.
- The author develops **Neural Designer**, the desktop ML application built on the **OpenNN** C++ library, and uses
  this project as its showcase. Training happens in the Neural Designer app on purpose (screenshots, architecture
  image), even though OpenNN alone could do it.
- Pipeline: collect the reviews of a business (case study: *Centro Comercial El Tormes*, Salamanca, 11,017 Google
  reviews) → classify each one as Good / Bad → Streamlit app and Power BI dashboard, refreshed at a configurable
  interval → everything in Docker.
- The model is trained in Neural Designer and runs with OpenNN (small C++ predictor), not with the heavy Neural
  Designer engine.
- Talk to the author in **Spanish**. Code, comments and repository docs are in **English**.
- The author is new to web scraping and Power BI: explain those parts step by step.
- The author will not pay for any service: only free plans.

## Rules

- **Record every decision** in `docs/decision-log.md` (D-xxx entries: context, decision, alternatives considered,
  reasons). To change a decision, add a dated update to its entry instead of rewriting history. The log is the
  source for the final README and the LinkedIn post.
- **Never commit datasets, review data, Neural Designer projects or models** (`data/`, `*.nd`, `models/`), nor
  secrets (`.env`). The Amazon reviews licence forbids redistribution, and `.nd` reports contain review texts.
- **Privacy:** never store author names, photos or profile links of reviews (D-001, D-013). Show aggregated
  statistics and short excerpts, not the full set of texts. Never bypass CAPTCHAs or blocks.
- The text normalisation applied before the model lives only in `src/impacto/text.py`. Training and inference must
  both use it: the OpenNN tokenizer is ASCII-only (D-008).
- Compare every new model with the TF-IDF + logistic regression baseline (`training/baseline.py`, D-010).
- Commits: several small commits per topic, authored by the author with no Claude attribution (the author's
  `push-changes` skill). Push only when the author asks.

## Setup on a new computer

Tools: [uv](https://docs.astral.sh/uv/), Git, CMake ≥ 3.24 and a C++20 compiler (Visual Studio Build Tools on
Windows) for the OpenNN predictor. Neural Designer only to train or to open the projects. Docker is not set up yet.

```bash
uv sync --group analysis
uv run playwright install chromium                                   # only for scraping/explore_google_maps.py
uv run training/download_dataset.py
uv run training/prepare_dataset.py                                   # 10k per class, checksums in docs/dataset.md
uv run training/prepare_dataset.py --per-class 40000 --output-dir data/processed_40k   # data of model C
```

Copy by hand from the previous computer (not in the repository):
- `models/impacto_model_c.nd`: the selected model, frozen (D-014). Also `impacto.nd`, the working project, if needed.
- If `models/model_c/` is missing, export it again:
  `uv run --group analysis training/export_model.py models/impacto_model_c.nd models/model_c --threshold 0.44`
- Then build the predictor (`docs/inference.md`; CMake downloads OpenNN commit `5aa391c` from GitHub) and check it:
  `uv run --group analysis training/evaluate_inference.py` must give 88.5% accuracy on the hold-out set, and
  `training/check_parity.py` must match Neural Designer.

## Status (update when it changes)

Last update: 2026-10-23.

- Done:
  - Data and model: Amazon reviews in Spanish, two classes, ASCII normalisation. Model C trained in Neural Designer
    (40k reviews per class, no attention): 88.4% testing accuracy; TF-IDF baseline 90.0% (D-014).
  - Domain shift measured (D-011): ~90% on real hotel reviews, weaker on sarcasm and indirect reviews.
  - Inference with OpenNN (D-015): same AUC as Neural Designer, 88.5% on the hold-out set, threshold 0.44.
  - Licence AGPL-3.0-only (D-016); the app must link to its source code.
  - App architecture: Streamlit + Power BI on the same database (D-012).
  - Google Maps exploration (D-013, `scraping/explore_google_maps.py`): without a Google account only 5 reviews are
    visible; more reviews or sorting require signing in. The network data has exact timestamps for each review.
- Case study changed to **El Corte Inglés Princesa (Edificio Moda)**, Madrid: 13,706 Google reviews (D-001 update).
- D-017 accepted: Apify free plan, **zero cost** (no payment method on the account), reviews since 2019-01-01,
  actor `compass/google-maps-reviews-scraper` with `personalData: false`. The code keeps limits as parameters so
  others can pay for more; we never do.
  - Apify account (free, no payment method) and token in `.env`. Price measured: $0.60 per 1,000 reviews.
  - Downloaded 7,490 reviews (Oct 2021 to Oct 2026; the cap was reached before 2019) for $4.49; ~$0.47 of credit
    left until 25 Nov 2026. Raw JSON in `data/reviews/`, database `data/impacto.db` (D-018), 3,063 Spanish reviews
    classified by model C.
  - First results (D-019): model C agrees with the stars 87.1% (AUC 0.94) on this real business; 1–2★ reviews and
    predicted-bad texts are growing (22% → 34% bad from 2021 to 2026).
- Next:
  1. Analyse the bad reviews: topics (parking, service, prices…) and peaks (sales, Black Friday, Christmas).
  2. Streamlit app (search box, % good/bad, evolution over time, stars vs. prediction, link to the source code)
     and Power BI on the same data (PostgreSQL when moving to Docker).
  3. Daily update of new reviews (~2 a day, within the free credit).
  4. Docker.
  5. Project write-up and LinkedIn post: architecture images from `models/impacto_model_c.nd`, before/after model
     curves, the model vs. stars agreement (87.1%) and the trend of bad reviews (see D-019 and "Ideas for later").
