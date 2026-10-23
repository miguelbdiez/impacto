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
- **Waiting for the author's decision: D-017.** Proposal: Apify free plan (no card) for the full history of El
  Tormes once, then daily updates of new reviews only, within the free credit. The author had also suggested a
  secondary Google account scraping every hour; not recommended (account blocks, terms of service).
- Next, once D-017 is decided:
  1. The author creates the Apify account and puts the token in `.env` (`APIFY_TOKEN=...`).
  2. Apify client (full and incremental download) and importer to our format, dropping author data. Test with
     ~50 reviews first.
  3. Database, Streamlit app (search box, % good/bad, evolution over time, stars vs. prediction) and Power BI.
  4. Docker.
  5. Project write-up and LinkedIn post: architecture images from `models/impacto_model_c.nd`, before/after model
     curves, and the "bad reviews vs. construction works" idea (see "Ideas for later" in the decision log).
