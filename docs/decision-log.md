# Decision Log — impacto

This file records the process and every relevant decision of the project: what was decided, which
alternatives were considered and why. It is the raw material for the final README and the LinkedIn post.

Status values: **Accepted** (decided), **Proposed** (recommendation pending confirmation), **Open** (still being researched).

---

## D-001 · Project scope

- **Date:** 2026-10-22
- **Status:** Accepted

**Context.** Portfolio project to show an end-to-end machine learning + data analysis workflow in a public
GitHub repository, documented in a LinkedIn post.

**Decision.** The user enters the name of a business and gets a dashboard that summarises what people think
about it (share of good and bad reviews, evolution over time, etc.). The live case study will use the reviews of a
single high-volume business, **anonymised** (no author names or identifiers are stored or published).
Those reviews are used only to demonstrate the system, **not to train** the model.

**Future scope.** Classify text that has no star rating (forums, social media posts). This is the reason to train a
text classifier instead of simply averaging stars.

---

## D-002 · Classification target: good / bad

- **Date:** 2026-10-22
- **Status:** Accepted, amended the same day to three classes (see update at the end of this entry)

**Decision.** Two classes: `good` and `bad`. When the labels come from star ratings: 1–2 stars → `bad`,
4–5 stars → `good`, 3 stars → excluded from training.

**Why.** Three-star reviews are ambiguous (mixed opinions), and including them as a class adds label noise.
A binary model is easier to train, evaluate and explain. A `neutral` class can be added later.

**Update (2026-10-22): three classes.** 3-star reviews are kept as a `Neutral` class:
1–2 stars → `Bad`, 3 stars → `Neutral`, 4–5 stars → `Good`.

*Why.* Real opinions are not only good or bad. Mixed comments ("good product but late delivery") are common, and in
the dashboard it is more honest to show them apart than to force them into one side. It also matters for the
future goal of classifying forum and social media text, where many messages are neither positive nor negative.

*Trade-off.* `Neutral` is the hardest class: 3-star texts mix praise and complaints, so most errors are expected
between `Neutral` and its neighbours. The confusion matrix will show it. Classes are balanced in the training file
(10k each) so the model does not simply ignore `Neutral`.

**Update (2026-10-23): back to two classes.** `Good` (4–5 stars) and `Bad` (1–2 stars); 3-star reviews are dropped
again.

*Why.* The three-class experiments (D-009, D-010) showed that `Neutral` concentrated most errors: the networks
recognised 49–56% of neutral reviews, and even the baseline only 55–59%. Meanwhile, confusing a good review with a
bad one happened in just 4–9% of cases. Stars give a reliable label for the two extremes and a noisy one for the
middle. A binary model is more accurate and easier to explain in the dashboard and the post. The three-class results
are kept in this log as part of the process.

---

## D-003 · Neural Designer for training, OpenNN for inference

- **Date:** 2026-10-22
- **Status:** Accepted (technical feasibility still to be verified)

**Context.** Neural Designer (desktop application) is built on top of OpenNN (open-source C++ library). The project
author develops Neural Designer, so the project also serves as a showcase of that work.

**Decision.** Train the text classification model in the Neural Designer desktop application, then run the
predictions in production with OpenNN.

**Alternatives considered.**
- *Train and predict with OpenNN only:* technically possible, but loses the visual/desktop part of the story.
- *Use the Neural Designer text-classification export:* it ships the generated `.py` plus the full application
  engine and its DLLs, too heavy to put in a Git repository.

**Why.** The desktop app gives a clear, visual training story (good for the architecture diagram and the post).
OpenNN keeps the deployed part light: it can be compiled inside the Docker image instead of committing binaries.

**Main risk.** The text preprocessing at prediction time (tokenisation, vocabulary, stop words, stemming…) must match
the one Neural Designer applied during training **exactly**, otherwise predictions are silently wrong. This
must be checked before building the rest of the pipeline.

---

## D-004 · Languages

- **Date:** 2026-10-22
- **Status:** Accepted

- Reviews: **Spanish only** for now.
- Code, comments and repository documentation: **English** (standard practice, larger audience).
- LinkedIn post: **Spanish**.

---

## D-005 · Training dataset

- **Date:** 2026-10-22
- **Status:** Accepted: Amazon Reviews, Spanish subset (see update at the end of this entry)

**Context.** A single business does not have enough reviews to train a model (a few hundred at most, mostly 4–5 stars),
so training data must come from a public dataset. The goal was to find a Spanish equivalent of the Amazon Reviews
example shipped with Neural Designer.

**Candidates found.**

| Dataset | Domain | Size | Labels | Licence / access | Notes |
|---|---|---|---|---|---|
| Amazon Reviews Multi — Spanish subset (`SetFit/amazon_reviews_multi_es`, `mteb/amazon_reviews_multi`) | Products (Amazon) | 200k train / 5k val / 5k test, balanced (20% per star) | 1–5 stars | Amazon licence: non-commercial, no redistribution. Officially withdrawn by Amazon (marked *defunct* on Hugging Face); community mirrors remain | Same family as the Neural Designer example. Large and balanced. Domain shift: products ≠ restaurants |
| Rest-Mex 2023 / 2025 (IberLEF, ODESIA portal) | TripAdvisor: restaurants, hotels, attractions (Mexico, Cuba, Colombia) | ~360k (2023) / ~297k (2025) | 1–5 polarity | Registration required on the ODESIA portal; research use | Best domain match. Latin American Spanish. Likely skewed towards 5 stars |
| COAR (SINAI group, Univ. of Jaén) | TripAdvisor restaurants in Spain | 2,202 | 1–5 (565 / 246 / 188 / 333 / 870) | CC BY-NC-SA 4.0, gated on Hugging Face | Too small to train, ideal as an **external test set** for the restaurant domain |
| `beltrewilton/punta-cana-spanish-reviews` | Hotels, Dominican Republic | 34.5k | 1–5 | MIT (as declared by uploader) | Mixed Spanish/English text, unclear provenance |
| `mrcsgh/horeca-spanish-reviews` | Bars, restaurants, cafés | ~5.5k | Score + category | MIT | **Synthetic** reviews, not representative of real language |

Discarded: English-only datasets (Yelp, TripAdvisor hotel reviews, 515K Booking reviews) and tweet corpora
(different register, small).

**Proposal.**
1. Use **Amazon Reviews ES** as the first training set: zero access friction and directly comparable with the
   Neural Designer example. Binarised following D-002 it gives ~80k `good` / ~80k `bad`.
2. Register for **Rest-Mex** in parallel as a domain-specific alternative.
3. Evaluate both models on **COAR** (real restaurant reviews from Spain) and keep the one that generalises better.
   The comparison "trained on products vs. trained on tourism, tested on restaurants" is itself a good result to report.

**Constraints.**
- No dataset is committed to the repository (all real-data licences forbid redistribution). The repo will include a
  download script and the data folder will be git-ignored.
- All real-data options are licensed for non-commercial / research use. This is a personal portfolio project, but it
  showcases a commercial product. The author should confirm this is acceptable.

**Update (2026-10-22): decision.**
- **Amazon Reviews ES** is the training dataset. The project is a flexible portfolio exercise, so the live case
  study can be a business that sells products instead of a restaurant, which removes most of the domain-shift
  concern. COAR and Rest-Mex are kept as optional future experiments.
- **Mirror with the original columns.** The first candidate mirror (`SetFit/amazon_reviews_multi_es`) only keeps
  `id`, `text` and `label`. The `buruzaemon/amazon_reviews_multi` mirror keeps the original files, with
  review title, product category and anonymised product / reviewer ids. It was chosen because Neural Designer accepts
  several columns, and the extra metadata is useful for exploration and error analysis.
- **Data never enters the repository.** Instead, the repo documents the source and every transformation step, and
  ships the scripts that rebuild the files (`training/`, `docs/dataset.md`).

---

## D-006 · Dashboard: Power BI without a paid licence

- **Date:** 2026-10-22
- **Status:** Proposed

**Context.** The author has no Power BI licence and wants to learn Power BI basics. Data should look "semi-real-time",
with configurable intervals (e.g. every 10 minutes for large businesses, every hour for small ones).

**Findings.**
- **Power BI Desktop** is free and Windows-only. It cannot run inside Docker.
- *Automatic page refresh* only works with **DirectQuery** sources (not Import mode). In **Desktop there is no
  restriction** on the interval (down to one second).
- In the **Power BI service** without dedicated capacity (free / Pro): automatic page refresh minimum is 30 minutes,
  scheduled refresh is limited to 8 per day, and querying a local database requires an on-premises gateway.
  A free licence only has *My workspace*; the only way to share is *Publish to web*, which makes the report public.

**Proposal.**
- Phase 1 (local): Docker runs the scraper, the model and a **PostgreSQL** database. **Power BI Desktop** connects
  to PostgreSQL in DirectQuery mode with automatic page refresh. Fully free and close to real time.
- The `.pbix` file is versioned in the repo, with screenshots / GIF for the README and the post.
- The scraping interval (how often new data arrives) is configured in the backend, independently of the dashboard.
- Server phase: Power BI service limits make it a poor fit without a licence. Re-evaluate then; a likely option is an
  additional lightweight web dashboard (e.g. Streamlit or Grafana) shipped in Docker, which also helps people
  cloning the repo on macOS/Linux.

---

## D-007 · Training file for Neural Designer

- **Date:** 2026-10-22
- **Status:** Accepted

**Decision.** One UTF-8, tab-separated file with a header, keeping the metadata columns:
`review_id, product_id, reviewer_id, product_category, stars, review_title, review_body, sentiment`.
Only `review_body` is used as input and `sentiment` as target. The rest are set to *Unused* in Neural Designer
(full table in `docs/dataset.md`).

**Why.**
- *Tab separator and text cleaning:* reviews contain commas and semicolons but never tabs once whitespace is
  normalised. Double quotes are replaced because the OpenNN reader switches to quoted-field parsing when it finds one
  (checked in `opennn/dataset/field_parsing.cpp`).
- *Keep the metadata columns:* showing in Neural Designer how each column gets a role (ID, input, target, unused) is
  part of the story, and `product_category` allows analysing errors per category.
- *`stars` must be Unused:* the target is derived from it (data leakage).
- *`review_title` is not an input:* the model must work on text without a title (Google reviews, social posts).
- *10k reviews per class by default:* the example shipped with Neural Designer has 1,000 reviews. 10k per class is
  enough for a solid model with reasonable training time. With two classes (D-002 update) the file has 20,000
  reviews, and the script can generate up to ~80k per class.
- *Separate hold-out file (official test split):* lets us check later that OpenNN, deployed in Docker, reproduces
  the Neural Designer results on reviews neither of them has seen.

*Update:* the text cleaning was extended into a full ASCII normalisation, see D-008.

**Note about the dashboard.** The dashboard will not read this training file. It will read the reviews collected from
the live business, which will carry their own fields (date, stars, text, predicted sentiment and probability, source,
etc.). This file only teaches the model.

---

## D-008 · Text normalisation to ASCII (OpenNN tokenizer limitation)

- **Date:** 2026-10-22
- **Status:** Accepted

**Context.** The vocabulary of the first trained model contained fragments such as `m`, `s`, `n`, `est` and `peque`
among its most frequent tokens. The cause is in the OpenNN word tokenizer (`for_each_token` in
`opennn/core/string_utilities.cpp`): it classifies the text byte by byte with `isalnum()` / `ispunct()`. In UTF-8 the
letters á, é, í, ó, ú, ñ, ü and the signs ¿ ¡ take two bytes that are neither alphanumeric nor punctuation, so they
are dropped and the word is split:

| Text | Tokens |
|---|---|
| más | `m`, `s` |
| pequeño | `peque`, `o` |
| también | `tambi`, `n` |
| mañana | `ma`, `ana` |

This affected **7.5% of the words** of the dataset ("más" appears 4,381 times, "está" 2,515).

**Alternatives considered.**
- *A. Normalise the text in our pipeline:* transliterate to ASCII before training and before predicting.
- *B. Make the OpenNN tokenizer UTF-8 aware:* the right long-term fix (the minimal version treats bytes ≥ 0x80 as
  part of a word), but it needs a new Neural Designer release before it can be used here.

**Decision.** A now, implemented once in `src/impacto/text.py` (`normalize_text`) and imported both by the training
data preparation and, later, by the inference service. A single function guarantees that training and prediction
see exactly the same tokens. B will be reported to the OpenNN team.

**Consequences.**
- Every word is kept whole (`mas`, `esta`, `pequeno`).
- Distinctions that depend on accents or ñ are lost (está / esta, año / ano). This is irrelevant for sentiment.
- Vocabulary of `review_body`: 24,923 distinct tokens, 14,429 of them appear at least twice.
- The first model, trained before this fix, is kept as a baseline to compare with.

---

## D-009 · Network architecture and training strategy

- **Date:** 2026-10-22
- **Status:** Proposed (to be confirmed with the second training)

**Context.** The first model was trained with a custom configuration. It was reviewed against the data and the
OpenNN source code before training again.

| Setting | Model 1 (baseline) | Model 2 (proposed) | Why |
|---|---|---|---|
| Text inputs | title + body | **body only** | Live reviews and social posts have no title, and OpenNN expects the same text columns at inference |
| Sequence length | 256 | **128** | Median review is 28 tokens and 98.6% fit in 128. Attention cost grows with the square of the length |
| Vocabulary | 20,000, min. frequency 1 | **min. frequency 2** (~14.4k) | Tokens seen only once are mostly typos and add noise |
| Embedding | 64 + positional encoding | same | Enough for 30k reviews |
| Attention | 3 layers, 16 / 8 / 4 heads | **1 layer, 4 heads** | Head size is 64 / heads: 16 heads give 4-dimensional heads, too small. The layers are stacked without residual connections, normalisation or feed-forward (full Transformer blocks in OpenNN add `Addition` and `Normalization3d` layers), so stacking adds cost and instability with little gain on short texts. The OpenNN default text classification network uses one layer with 4 heads |
| Pooling | average | same | Ignores padding (checked in `pool3d_operator.cpp`) |
| Dense | 32 (tanh) + 16 (ReLU) | **one layer, 32–64 ReLU** | A second hidden layer adds nothing with 30k samples |
| Output | softmax, 3 classes | same | — |
| Loss | cross-entropy | same | Correct for multi-class |
| Optimiser | Adam, learning rate 0.001, batch 64 | same | Standard values |
| Regularisation | none | **L2, 0.001** | ~1.3M parameters (almost all in the embedding table) for 18k training samples |
| Early stopping | disabled (max. validation failures ≈ 9.2·10¹⁸) | **10 failures** | Stop when the selection error stops improving |
| Epochs | 75 | 75 as an upper bound | With early stopping it will likely stop earlier |
| Model selection | growing inputs / neurons configured | **not run** | Not meaningful for this network and multiplies training time |

Data split: 60% training / 20% selection / 20% testing (18k / 6k / 6k), unchanged.

**Model 1 results (baseline).** Full figures and error history in `training/results/model1_baseline.json`.

- 75 epochs in 8 min 25 s on an RTX 5070 Ti.
- The selection (validation) error reached its minimum, 0.819, at **epoch 6** and then climbed to ~2.2 while the
  training error kept falling to ~0.07: **clear overfitting**. Neural Designer kept the parameters of the best epoch,
  so the reported model is the epoch-6 one. The other 69 epochs (~7.5 minutes) were wasted.
- Testing accuracy: **62.8%** (3 classes, so random guessing gives 33%).

| Class | Recall | Precision |
|---|---|---|
| Bad | 71.0% | 64.3% |
| Good | 68.9% | 69.8% |
| Neutral | 48.6% | 53.3% |

- As expected, `Neutral` is the hardest class. Most errors are between `Neutral` and the other two, while `Good`
  and `Bad` are rarely confused with each other (153 and 200 out of ~2,000 each).
- These results support the proposed changes: early stopping (stop around epoch 16 instead of 75), L2
  regularisation against overfitting, and a smaller network.

**Model 2 results.** Normalised text, body only, sequence 128, 1 attention layer with 4 heads, dense 64 ReLU.
Trained for a fixed 7 epochs (no regularisation, minimum token frequency 1). Figures in
`training/results/model2.json`.

| | Model 1 | Model 2 |
|---|---|---|
| Inputs | title + body | body only |
| Training time | 8 min 25 s (75 epochs) | **42 s (7 epochs)** |
| Best validation epoch | 6 | 5 |
| Testing accuracy | 62.8% | 62.8% |
| Recall bad / good / neutral | 71.0% / 68.9% / 48.6% | 63.7% / 68.6% / **56.3%** |
| Good ↔ bad errors | 8.8% | **6.9%** |

Same accuracy, but 12 times faster, without depending on the title (which is a strong signal in Amazon reviews),
more balanced across classes and with fewer polarity errors. Model 2 is the better base.

**Issues observed in the saved Neural Designer project** (to investigate, possible bugs):
- The minimum token frequency, the regularisation type and the maximum validation failures changed in the interface
  did not appear in two consecutive saves of the `.ndm`.
- After the model 2 training, the saved `.ndm` lists every column as input (`stars` included), and its vocabulary
  was built from all of them. The training curve is the same as the other models, which would not happen if `stars`
  had been used. The roles were probably changed after training, leaving parameters and vocabulary out of sync.
- One intermediate run trained normally (best validation error 0.80) but tested at 32.4%, chance level for three
  classes. This is consistent with the same mismatch between the trained parameters and the vocabulary.

Before exporting a model, check that the saved `.ndm` has the expected roles and vocabulary.

---

## D-010 · Reference baseline: TF-IDF + logistic regression

- **Date:** 2026-10-22
- **Status:** Accepted

**Context.** Models 1 and 2 both reached 62.8%. To know whether that is the ceiling of the data or a limit of the
network, a classic model was trained on the same file (`training/baseline.py`). It uses `review_body` only and the
same proportions as Neural Designer (60% training, 20% testing).

| Training reviews | Testing accuracy | Hold-out accuracy* | Recall bad / good / neutral (testing) | Good ↔ bad errors |
|---|---|---|---|---|
| 18,000 (file with 10k per class) | **65.8%** | 67.2% | 70.6% / 72.1% / 54.7% | 5.2% |
| 72,000 (file with 40k per class) | **68.0%** | 69.6% | 72.4% / 75.7% / 55.9% | 4.0% |

\* Balanced accuracy, because the hold-out set has half as many neutral reviews.

**Conclusions.**
- The Neural Designer network (62.8%) is **3 points below** a linear model trained on the same 18k reviews. This is
  common: an attention network trained from scratch needs more data than a bag-of-words model.
- More data helps: going from 18k to 72k training reviews adds about 2 points to the baseline, and a neural network
  is expected to benefit more.
- The labels set a ceiling. 3-star reviews mix praise and complaints, and even the baseline only recognises 55–59%
  of them. On the other hand, confusing a good review with a bad one is rare (4–7% depending on the model).

**Next experiments in Neural Designer** (goal: match or beat the baseline):
1. Train with 40k reviews per class (`prepare_dataset.py --per-class 40000`).
2. L2 regularisation 0.001 and minimum token frequency 2, if they are kept in the project.
3. Remove the attention layer (embedding → average pooling → dense). This simpler model is usually strong for
   sentiment on short texts.

**Update (2026-10-23): baseline with two classes** (D-002 update), same script and proportions:

| Training reviews | Testing accuracy | Hold-out accuracy | Recall bad / good (testing) |
|---|---|---|---|
| 12,000 (file with 10k per class) | **88.2%** | 88.6% | 90.2% / 86.1% |
| 48,000 (file with 40k per class) | **90.0%** | 90.1% | 90.9% / 89.0% |

These are the new figures to beat. The next experiments stay the same.

---

## Open questions

- Exact Neural Designer export format for text classification models and how to load it in OpenNN (D-003).
- Data source for the live case study (Google Maps, TripAdvisor…), and the legal/terms-of-service implications of
  scraping it. To be studied in the scraping phase.
