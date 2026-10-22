# impacto: notes for Claude Code

## Context

- Portfolio project. The goal is a public GitHub repository plus a LinkedIn post (in Spanish) showing an end-to-end
  machine learning project.
- The author develops **Neural Designer**, the desktop ML application built on the **OpenNN** C++ library, and uses
  this project as its showcase. Training happens in the Neural Designer app on purpose (screenshots, architecture
  image), even though OpenNN alone could do it.
- Pipeline: scrape the reviews of a business → classify each one as Good / Neutral / Bad → Power BI dashboard
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
- Neural Designer: proprietary; the author has the sources and the installed application.
- OpenNN: https://github.com/Artelnics/opennn

## Status (update when it changes)

Last update: 2026-10-22.

- Done:
  - Training dataset and ASCII normalisation.
  - Models 1 and 2: 62.8% testing accuracy on 3 classes. Results in `training/results/`.
  - Baseline: 65.8% with 18k training reviews, 68.0% with 72k.
- Waiting: the author is fixing a Neural Designer bug. Column roles and some training settings were not persisted
  in the saved project (details in D-009).
- Next:
  1. Experiments listed in D-010 (40k reviews per class, L2 regularisation, network without attention).
  2. Inference with OpenNN.
  3. Scraper, with its source and legal terms still to be decided.
  4. Database and Power BI dashboard.
  5. Docker.
