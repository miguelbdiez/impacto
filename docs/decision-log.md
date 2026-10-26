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

**Update (2026-10-26): case study.** The live case study is **El Corte Inglés Princesa (Edificio Moda)**, Calle de
la Princesa 56, Madrid (Moncloa–Argüelles): 4.2 stars, 13,706 Google reviews. A nationally known brand makes the
project more relatable than a local shopping centre. El Corte Inglés Castellana was discarded (42,151 reviews, too
many for the free plan of D-017). *Centro Comercial El Tormes* (Salamanca) remains the place used to explore Google
Maps (D-013). The analysis is presented neutrally, with aggregated figures, no logos and a note that it is an
educational analysis of public reviews, not affiliated with the company.

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

**Neural Designer binary models** (results in `training/results/`). After the author fixed the bug noted in D-009,
the saved project keeps the column roles, the minimum token frequency and the regularisation. The vocabulary has
11,477 tokens: the 11,473 words that appear at least twice, as predicted in `docs/dataset.md`, plus 4 control
tokens. This confirms that our simulation of the OpenNN tokenizer is exact.

| Model | Data | Network | Training | Epochs (best) | Testing accuracy | Recall bad / good |
|---|---|---|---|---|---|---|
| 3 | 10k per class | 1 attention layer, 4 heads, dense 64 | L2 0.001, batch 32, 5 epochs max. | 5 (5) | 84.0% | 82.9% / 85.1% |

Model 3 stopped while the validation error was still falling (0.479 → 0.362): it had not converged yet. Next run:
more epochs with early stopping.

---

## D-011 · Domain shift: from product reviews to business reviews

- **Date:** 2026-10-23
- **Status:** Accepted (measurement); the plan below is proposed

**Context.** The model is trained on Amazon product reviews, but it will classify reviews of businesses
(restaurants, shops, hotels…), which talk about service, staff, waiting times or atmosphere. How much accuracy is
lost when the domain changes?

**Measurement** (`training/domain_shift.py`). The TF-IDF + logistic regression baseline was tested on two public
Spanish datasets from the hospitality sector (MIT licence, downloaded to `data/external/`, not committed):
- **Punta Cana hotel reviews:** 32,801 real reviews in Spanish, 93% positive. Balanced accuracy on a 30% test split.
- **HorecaReviews-ES:** 4,655 **synthetic** reviews of bars, cafés and restaurants, written in styles designed to be
  difficult (sarcastic, anecdotal, constructive…).

| Trained on | Amazon (testing) | Hotels | Bars and restaurants |
|---|---|---|---|
| Amazon, 12k reviews | 88.2% | **90.4%** | **73.8%** |
| Amazon, 48k reviews | 90.0% | 92.2% | 78.0% |
| Hotels only, 23k reviews | — | 94.9% | 69.7% |
| Amazon 12k + hotels 23k | — | 92.2% | 78.5% |

Accuracy on bars and restaurants by style (Amazon 48k): sarcastic 47%, anecdotal 66%, constructive 80%, critical 82%,
enthusiastic 85%, short 88%.

**Conclusions.**
- On **real business reviews** (hotels) the Amazon model works well: 90–92%, only 3–5 points below a model trained
  on hotel reviews. General sentiment vocabulary ("excelente", "horrible", "no lo recomiendo") is shared across domains.
- The hard part is the **style**, not the sector: sarcasm is a coin toss and indirect, anecdotal reviews are often
  missed. A model trained only on hotels does even worse on the bar reviews (69.7%).
- More Amazon data helps in every domain (+2 to +4 points), and mixing in data from the target domain helps most.

**Plan.**
1. Train with more Amazon data (40k reviews per class).
2. Google reviews come **with stars**, so every collected review is also a free labelled example. The dashboard can
   show how often the predicted sentiment agrees with the stars: continuous monitoring of the model in its real
   domain.
3. If that agreement is low, retrain adding labelled reviews from many businesses (collected by the scraper) or the
   Rest-Mex corpus (restaurants and hotels, registration required).
4. The model's real value is for text **without** stars (forums, social media). The starred reviews are the way to
   validate it.

---

## D-012 · Application: Streamlit app + Power BI dashboard

- **Date:** 2026-10-23
- **Status:** Accepted (updates D-006)

**Context.** The app works like this: the user types the name of a business (e.g. *El Tormes Mall*, a shopping
centre in Salamanca), the app collects its reviews, classifies them with the model and shows charts and statistics.
A Power BI report only reads data, so it cannot start the collection for a new business from a text box.

**Decision.**
- **Streamlit** web app (Python, runs in Docker) for the search box, on-demand collection and charts. This is what
  anyone cloning the repository will use.
- **Power BI Desktop** connected to the same database (DirectQuery + automatic page refresh, D-006) as an analysis
  dashboard for the businesses being tracked, which are re-collected at a configurable interval.
- Until OpenNN inference is ready, the app uses the TF-IDF baseline as a stand-in model behind the same interface.

**Alternatives considered.** Streamlit only (simpler, but drops the Power BI learning goal). Power BI only (no
search box: businesses would be listed in a configuration file).

---

## D-013 · Review collection: own scraper with Playwright

- **Date:** 2026-10-23
- **Status:** Accepted

**Options evaluated.**

| Option | Reviews | Cost | Notes |
|---|---|---|---|
| Google Places API (official) | 5 per place at most | Free quota | Allowed, but useless for statistics |
| Scraping service (Apify, Outscraper, SerpApi) | All | Free tiers of ~500–10,000 reviews per month | The provider does the scraping; stable |
| Own scraper with Playwright (automated browser) | All | Free | Against Google's terms of service; breaks when the page changes; most learning |

**Decision.** Own scraper with Playwright. The author wants to learn web scraping hands-on, which is part of the
project's goal.

**Consequences and safeguards.**
- **Terms of service:** Google does not allow automated access to Maps. The README states that the scraper is for
  educational purposes and that whoever runs it is responsible for complying with the terms of the site.
- **Privacy (GDPR):** only public data is collected, without login. Author names, photos and profile links are never
  stored: only rating, date, text and whether the owner replied (D-001).
- **Low load:** small volumes, pauses between actions, results cached in the database so each review is
  downloaded once.
- **Fragility:** the CSS selectors live in a single module, so a change in Google's page is fixed in one place.
  Tests run against saved HTML pages.
- The collector sits behind an interface, so a service such as Apify could be added later without touching the rest.

**Update (2026-10-23): fallback and priority.** If scraping proves unworkable, the reviews will be loaded from a CSV
with the same format and passed through the app; only the collection step changes. For this portfolio project the
way the data is obtained matters less than training the model well, running inference and interpreting the results.
The OpenNN inference therefore goes first, before the scraper.

**Update (2026-10-23): exploration results.** A guided exploration with a visible browser (Playwright, no Google
account) on *Centro Comercial El Tormes* (4.2 stars, 11,017 reviews) found:
- **Without signing in, Google Maps shows a "limited view": only 5 reviews.** Scrolling loads nothing more. Both
  "Ver más reseñas (11.012)" and the "Ordenar" (sort) button open a sign-in prompt.
- **The data carries exact dates.** The reviews arrive through an internal request (`batchexecute`, rpc `qv9Egd`)
  where each review has a timestamp in microseconds (e.g. 2026-01-18 15:59:14 UTC), although the page only shows
  "Hace 9 meses". The construction-works idea is therefore feasible if the reviews can be obtained.
- The data captured during the exploration (author names and profiles) was deleted after the analysis.

Consequence: a scraper without an account gets the same 5 reviews as the official Places API. Getting all of them
requires either automating a signed-in Google account or a service that does the collection. Decision pending.

---

## D-014 · Selected model

- **Date:** 2026-10-23
- **Status:** Accepted: run C. The project with its trained parameters is frozen as `models/impacto_model_c.nd`
  (git-ignored). It will also provide the architecture images for the project write-up.

**Runs compared.** All binary, normalised text, body only, sequence 128, minimum token frequency 2, embedding 64,
dense 64 ReLU + sigmoid output, Adam (learning rate 0.001), L2 0.001, early stopping after 5 epochs without
improvement (the best epoch's parameters are restored). Full figures in `training/results/binary_runs.json`.

| Run | Data | Network | Epochs (best) | Time | Testing accuracy | Recall bad / good | AUC (95% CI) | Baseline on same file |
|---|---|---|---|---|---|---|---|---|
| A | 10k per class, batch 32 | with attention (1 layer, 4 heads) | 16 (11) | 1 s | 84.8% (4,000) | 86.6% / 83.1% | 0.922 (0.915–0.929) | 88.2% |
| B | 40k per class, batch 64 | with attention (1 layer, 4 heads) | 14 (9) | 6 s | 88.6% (16,000) | 88.3% / 88.8% | 0.956 (0.953–0.958) | 90.0% |
| C | 40k per class, batch 64 | **without attention** | 22 (17) | 4 s | 88.4% (16,000) | 88.3% / 88.6% | 0.953 (0.950–0.956) | 90.0% |

**Findings.**
- **More data is what matters:** from 10k to 40k reviews per class the accuracy rises by almost 4 points (84.8% → 88.6%)
  and the gap with the baseline shrinks from 3.4 to 1.4 points.
- **Attention adds nothing here.** B and C differ by 20 reviews out of 16,000 (the standard error is ±0.25%), with
  overlapping AUC intervals and the same split. Short reviews are classified by the words they contain, more than by
  their order.
- The TF-IDF baseline with word pairs is still 1.4–1.6 points ahead. It captures expressions such as "no recomiendo"
  directly. This can be revisited later (more data, larger embedding).

**Proposal: run C (without attention).**
- Same accuracy as B.
- **Simpler and faster to deploy:** four layers instead of six. Prediction with OpenNN in Docker will run on CPU, and
  the cost of attention grows with the square of the text length.
- It is the network whose parameters are saved in the project now. Choosing B would mean training it again, because
  a `.nd` keeps only the last trained network.
- It is a good message for the post: the simpler model is as good as the attention one.

---

## D-015 · Inference with OpenNN

- **Date:** 2026-10-23
- **Status:** Accepted (resolves the main risk of D-003); decision threshold pending

**Context.** The Neural Designer deploy package ships the whole application engine, too heavy for the repository.
The goal was to run the trained model (run C, D-014) with OpenNN alone.

**What a Neural Designer project contains.** The `.nd` file stores the network and its parameters in OpenNN's own
formats: a network JSON and a binary parameter file with the `OPENNNP` header. The vocabulary is in the project
configuration (`.ndm`). Run C's network has no tokenizer layer, so the text is tokenised with OpenNN's
`WordLevelTokenizer` and that vocabulary, and the token ids go straight into the network. The source code confirms
that this encoding is the one used in training: `[START]`, tokens, `[END]`, zero padding up to 128.

**Implementation** (`docs/inference.md`).
- `training/export_model.py` extracts `model.json`, `model.bin`, `vocabulary.txt` and `model_info.json` (5.3 MB).
- `inference/predict.cpp` is a ~100-line C++ program linked with OpenNN, compiled for CPU only. CMake downloads
  OpenNN from GitHub at the pinned commit `5aa391c`, the version Neural Designer was built with, or uses a local
  checkout. The executable is 1.3 MB.
- `src/impacto/model.py` is the Python wrapper used by the app. It normalises the text (D-008), calls the predictor
  and returns probabilities. Texts without words (reviews with stars only) get no prediction instead of a guess.

**Validation.**
- **Same model as Neural Designer.** On the project's 16,000 testing samples (`training/check_parity.py`) the area
  under the ROC curve is 0.9532 in OpenNN and 0.953 in Neural Designer. With the threshold that predicts as many
  positives as Neural Designer (0.4397), the confusion matrices differ by at most 2 reviews per cell. Neural Designer
  therefore applies a decision threshold of about 0.44–0.45 (its ROC analysis reports 0.45 as optimal). The last 2
  reviews are explained by GPU versus CPU arithmetic.
- **Hold-out set** (3,993 reviews never seen by either tool, `training/evaluate_inference.py`): accuracy 88.5%,
  AUC 0.955. Predicted in 0.2 s on CPU.

| Threshold | Accuracy | Recall bad | Recall good |
|---|---|---|---|
| 0.50 | 88.5% | 90.6% | 86.4% |
| 0.44 | 88.5% | 88.2% | 88.8% |

**Decision threshold: 0.44** (decided 2026-10-23). It balances both classes (bad 88.2% / good 88.8% on the hold-out
set) and reproduces Neural Designer. It is stored in `model_info.json` (`--threshold` in the export), not hard-coded.

**Pending (optional).** Compare the probabilities one by one with the Neural Designer deploy package (`--reference`).

---

## D-016 · Licence: AGPL-3.0

- **Date:** 2026-10-23
- **Status:** Accepted

**Context.** The predictor (`inference/predict.cpp`) is linked with OpenNN, which is distributed under the GNU Affero
General Public License version 3 only (`AGPL-3.0-only`), or under a commercial licence from Artelnics. A program
built on top of an AGPL library and distributed, or offered to users over a network, has to be released under the
AGPL as well.

**Decision.** The whole repository is released under `AGPL-3.0-only`: the official text is in `LICENSE`, declared in
`pyproject.toml` and in the README.

**Consequences.**
- Anyone may use, study, modify and redistribute the project. Whoever distributes it, or runs a modified version as a
  service that other people use, must offer them the source code under the same licence.
- The Streamlit app will show a link to the repository, the usual way to meet the AGPL's network clause (section 13).
- The licence covers the code only. The datasets keep their own terms and are not included (D-005, D-011). Neural
  Designer is used only to train and is not distributed with the project.
- The Python dependencies (pandas, scikit-learn, h5py: BSD) are compatible with the AGPL.

---

## D-017 · Collecting the reviews: Apify free plan

- **Date:** 2026-10-23
- **Status:** Accepted on 2026-10-26, with a zero-cost rule (see the update at the end of this entry)

**Context.** The exploration (D-013 update) showed that without a Google account Maps only shows 5 reviews. The
author does not want to pay anything for a portfolio project.

**Free options evaluated.**

| Option | Reviews | Risk |
|---|---|---|
| Own scraper, no account | 5 per place | Useless for statistics |
| Own scraper with a signed-in (secondary) Google account | All, exact dates | Highest: automating an account is what Google polices first (account blocked, CAPTCHAs); anyone cloning the repo would need their own account |
| Apify free plan ($0, no card, ~$5 of credit per month) | All, exact dates | The provider does the collection; we only handle the data |
| Official APIs (Google Places, TripAdvisor, Yelp, Foursquare) | 3–5 per place, or paid | — |
| Google Business Profile API | All | Only for the owner or manager of the listing |

**Legal notes** (general information, not legal advice).
- In Spain this is not a crime in itself. It breaches Google's terms, a contract: the Google Maps additional terms
  forbid copying the content and "mass download or create bulk feeds of the content". The usual consequence is
  losing access or the account.
- It could become unlawful by bypassing security measures (CAPTCHAs, blocks; art. 197 bis of the Spanish Criminal
  Code), by mishandling personal data (GDPR: author names and profiles), or by republishing the review texts
  (authors' copyright and Google's database right against substantial extraction).
- A non-commercial portfolio lowers the risk but does not remove it, and the project is public under the author's
  name. Using Apify does not move the responsibility for how the data is used.

**Proposal.**
1. **Full history once** with an Apify Google Maps reviews actor: the ~10,000 most recent reviews with the official
   actor (~$0.50 per 1,000), or all 11,017 with a cheaper one. Prices to be confirmed on the actor's page.
2. **Daily update** of new reviews only (actors that sort by newest and stop at a start date or at already
   downloaded reviews). About 600 reviews a month, around $0.30, within the free credit. Hourly checks are not
   justified: El Tormes receives a few reviews a day.
3. **Safeguards:** the importer drops author names, photos and profile links. The dashboard shows aggregated
   statistics and short excerpts, never the full set of texts. CAPTCHAs or blocks are never bypassed.
4. The Apify token lives in `.env` (git-ignored), never in the code or the chat.
5. A first test with ~50 reviews before the full download.

The signed-in Google account option was proposed by the author (hourly updates) and is not recommended, for the
reasons above.

**Update (2026-10-26): other review sites checked.** Before deciding, other sites with opinions about businesses
were checked for *Centro Comercial El Tormes*. Google concentrates almost all of them: 11,017 reviews against 7 on
Yelp (apparently in English). There is no listing with opinions on TripAdvisor, Foursquare (its City Guide closed in
December 2024), Páginas Amarillas or Minube. Gastroranking republishes Google reviews. Trustpilot was also checked
for online shops (e.g. PcComponentes, 16,825 reviews in Spanish): only the ~10 most recent pages are visible without
an account (deeper pages ask to sign in and show a reCAPTCHA), and its `robots.txt` disallows every automated agent
except search engines. Technically easier, but more explicitly forbidden, so it was discarded.

**Update (2026-10-26): decision.** Apify free plan, with these rules:
- **Zero cost.** Only the free plan (~$5 of credit per month) and **no payment method added to the account**, so
  nothing can ever be charged. When the credit runs out, Apify stops the runs until the next month.
- **Reviews since 2019-01-01** of El Corte Inglés Princesa (D-001 update), sorted by newest.
- **Actor:** `compass/google-maps-reviews-scraper` (official). `personalData: false` makes it skip the reviewer's
  name, profile, photo and review URL **at the source**, so no personal data is ever collected. `publishedAtDate`
  gives the exact date.
- **The code supports paid use without us paying:** maximum reviews and maximum charge per run are parameters.
  Anyone with a paid plan can raise them; our runs stay within the free credit.
- **First a test run of ~50 reviews** to measure the real price per review on the free plan. Then the download is
  sized to fit the monthly credit, split over two months if needed.
- The reviews go into a database (local first, D-018 to be written).

**Update (2026-10-26): test run and full download.**
- The actor has no "only reviews with text" option. Its keyword filter (`reviewsFilterString`) was discarded: it
  would drop short reviews ("Genial", "Fatal") and bias the data. Reviews with stars only are kept: they count for
  the star statistics, and only the texts in Spanish go through the model.
- Test with 50 reviews (2 to 24 October 2026): every review has its exact date, 26 of 50 have text (22 Spanish,
  3 English, 1 French), and no reviewer field arrives. Real free-plan price: **$0.0006 per review ($0.60 per
  1,000)** plus $0.00005 per run start; the test cost $0.03. The account confirms plan FREE with a hard cap of $5 a
  month (cycle 26 October to 25 November) and keeps results for 7 days only, so every download is saved locally.
- Full download launched with `--since 2019-01-01 --max-reviews 7490 --max-charge-usd 4.50`, leaving ~$0.47 of
  this month's credit for tests, as decided by the author.
- **Incident:** while waiting for that run (`W4iERQ7BufPFqDKl5`), a network error (`IncompleteRead`) stopped the
  local script. The run itself kept going on Apify's servers: it had 6,680 reviews and $4.01 charged when it was
  found through the API. Starting a new run would have paid twice. The client was changed so that read requests are
  retried after network errors, the start request is never retried, the run id is printed as soon as it starts,
  results are downloaded in pages of 1,000, and `--run-id` resumes an existing run without paying again.
- **Result:** 7,490 reviews for $4.49 (the review cap was reached). They go from **29 October 2021** to 24 October
  2026: the shop receives more reviews than estimated (~1,500 a year), so the cap was reached before 2019.
  Completing 2019–2021 is not possible within the free plan: the actor only goes from newest to oldest, so it would
  have to download (and pay for) the last five years again. **The history used is therefore October 2021 to October
  2026**, five years. New reviews arrive at about 2 a day (~$0.04 a month), so updates fit in the credit left.

---

## Ideas for later

- **Bad reviews vs. construction works (El Tormes).** Plot the share of bad reviews over time and mark the periods
  of works in the shopping centre (taken from local news). If the bad reviews rise during the works and mention them,
  it is a real, explainable conclusion for the post. This requires the **exact date** of each review, not Google's
  relative dates ("hace 2 años").

---

## Open questions

- Whether to publish the trained model. `models/` is git-ignored for now: the weights and the vocabulary are derived
  from the Amazon reviews, whose licence does not allow redistributing the data (D-005).
- Whether Google Maps provides the exact date of each review, needed for the construction-works idea above (D-013).
