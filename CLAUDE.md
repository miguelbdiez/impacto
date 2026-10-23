# impacto: notes for Claude Code

## Context

- Portfolio project. The goal is a public GitHub repository plus a LinkedIn post (in Spanish) showing an end-to-end
  machine learning project.
- The author develops **Neural Designer**, the desktop ML application built on the **OpenNN** C++ library, and uses
  this project as its showcase. Training happens in the Neural Designer app on purpose (screenshots, architecture
  image), even though OpenNN alone could do it.
- Pipeline: scrape the reviews of a business → classify each one as Good / Bad → Power BI dashboard
  refreshed at a configurable interval → everything in Docker.
- The model is trained in Neural Designer. Predictions will run with OpenNN, compiled inside the Docker image instead
  of shipping the heavy Neural Designer engine.
- Talk to the author in **Spanish**. Code, comments and repository docs are in **English**.
- The author is new to web scraping and Power BI: explain those parts step by step.

## Rules

- **Record every decision** in `docs/decision-log.md` (D-xxx entries: context, decision, alternatives considered,
  reasons). To change a decision, add a dated update to its entry instead of rewriting history. The log is the
  source for the final README and the LinkedIn post.
- **Never commit datasets or Neural Designer projects** (`data/`, `*.nd`). The Amazon reviews licence forbids
  redistribution, and `.nd` reports contain review texts. Only scripts, documentation and metrics go in the repo.
- The text normalisation applied before the model lives only in `src/impacto/text.py`. Training and inference must
  both use it: the OpenNN tokenizer is ASCII-only (D-008).
- Compare every new model with the TF-IDF + logistic regression baseline (`training/baseline.py`, D-010).

## Setup on a new computer

```bash
uv sync --group analysis
uv run training/download_dataset.py
uv run training/prepare_dataset.py        # verify checksums in docs/dataset.md
```

Not in the repository:
- `data/`: regenerated with the commands above.
- `impacto.nd` (Neural Designer project): copy it by other means, or recreate it following
  `docs/neural-designer.md`. Inspect any saved project with `training/inspect_nd.py`.
- `models/` (the frozen project `impacto_model_c.nd` and the exported model): copy by hand, then rebuild the
  predictor as described in `docs/inference.md`.
- Neural Designer: proprietary; the author has the sources and the installed application.
- OpenNN: https://github.com/Artelnics/opennn

## Status (update when it changes)

Last update: 2026-10-23.

- Done:
  - Training dataset and ASCII normalisation.
  - Models 1 and 2 (3 classes): 62.8% testing accuracy, against a 65.8% baseline. Results in `training/results/`.
  - Back to 2 classes (Good / Bad, D-002 update). New baseline: 88.2% with 12k training reviews, 90.0% with 48k.
  - Domain shift measured (D-011): the Amazon baseline gets 90.4% on real hotel reviews and 73.8% on synthetic
    bar reviews (sarcasm is the weak spot).
  - The Neural Designer bug that lost column roles and settings is fixed.
  - Binary runs in Neural Designer (D-014): A 84.8%, B 88.6%, C 88.4%. Selected model: C (40k reviews per class, no
    attention), frozen in `models/impacto_model_c.nd` (git-ignored; copy it by hand to another computer).
  - App decided: Streamlit + Power BI (D-012). Scraper decided: own Playwright scraper (D-013). The author asked
    to wait before building the scraper.
  - Inference with OpenNN works (D-015, `docs/inference.md`): same AUC as Neural Designer, 88.5% on the hold-out
    set. Exported model in `models/model_c/` (git-ignored), predictor built in `build/inference/`.
  - Decision threshold 0.44 (D-015). Licence AGPL-3.0-only, required by OpenNN (D-016); the app must link to its
    source code.
- Next:
  1. Collect business reviews: Playwright scraper (D-013) or, as a fallback, a CSV. Exact review dates are needed
     (see "Ideas for later" in the decision log).
  2. Database, Streamlit app and Power BI dashboard.
  3. Docker (OpenNN is compiled from GitHub inside the image).
