# Training dataset

The sentiment model is trained on public Spanish product reviews from Amazon. The data is **not included in this
repository**: its licence does not allow redistribution. This document explains where it comes from and exactly how
it is transformed, so anyone can rebuild the same training file.

## Source

**Multilingual Amazon Reviews Corpus (MARC)**, Spanish subset.

- Paper: Keung, P., Lu, Y., Szarvas, G. and Smith, N. A. (2020). *The Multilingual Amazon Reviews Corpus.*
  Proceedings of EMNLP 2020.
- Reviews written between November 2015 and November 2019. Each review has a 1–5 star rating, and stars are
  balanced (20% each) in every split.
- Columns: `review_id`, `product_id`, `reviewer_id` (both anonymised by Amazon), `stars`, `review_title`,
  `review_body`, `language`, `product_category` (30 categories).
- Amazon withdrew the official download in 2023. The files are taken from the Hugging Face mirror
  [`buruzaemon/amazon_reviews_multi`](https://huggingface.co/datasets/buruzaemon/amazon_reviews_multi), which keeps the
  original files, pinned to commit `486fbd96a972291f6d7b4cad9d88088c5983244c`.

| Split | Reviews |
|---|---|
| train | 200,000 |
| validation | 5,000 |
| test | 5,000 |

### Licence

The corpus is distributed for **non-commercial research use** under Amazon's own terms: no redistribution, no
reselling, and no attempts to identify reviewers. That is why this repository only contains the scripts that download
and transform it.

## Rebuilding the training file

```bash
uv run training/download_dataset.py     # -> data/raw/{train,validation,test}.jsonl.gz
uv run training/prepare_dataset.py      # -> data/processed/reviews_es_{train,holdout}.csv + stats.json
```

`prepare_dataset.py` accepts `--per-class N` (default 10,000; `0` uses every review) and `--seed` (default 42).

The process is deterministic (pinned source commit, fixed seed, package versions locked in `uv.lock`). With the
default options the files must match these SHA-256 checksums:

| File | SHA-256 |
|---|---|
| `data/raw/train.jsonl.gz` | `7d9985b143cb33bf77eb2ffec962efd1ee527df95389e485482e2759f83cacba` |
| `data/raw/validation.jsonl.gz` | `797199f8c3e740be79b437005d30b3e82d236bbfa715937f7544125f15f373ac` |
| `data/raw/test.jsonl.gz` | `a0425ac99270b196d10585d45a3e3f6b3dc2ca757967c97034e83441d8a0f683` |
| `data/processed/reviews_es_train.csv` | `9a637e1911e2c6515cd028bcc71242f27434dbc1c47e95c7b2719dcb73fd7155` |
| `data/processed/reviews_es_holdout.csv` | `28f70c6ee599f96b07121373df26c8b8048a3ee3635a59a6a1fd5266ddd67fc9` |

## Processing steps

1. **Text normalisation** (decision D-008). `review_title` and `review_body` go through
   `impacto.text.normalize_text`, the same function that will be applied to new reviews before predicting:
   - Accents are removed and the text becomes plain ASCII (`más` → `mas`, `pequeño` → `pequeno`). The OpenNN word
     tokenizer drops the bytes of accented letters and splits the word in two (`más` → `m` + `s`), which affected
     7.5% of the words.
   - Opening `¿` and `¡` are removed. Typographic quotes, double quotes included, become single quotes: OpenNN
     switches to quoted-field parsing as soon as a file contains a double quote.
   - Every run of whitespace (tabs and line breaks included) becomes a single space, so each line is exactly one
     review with the same number of fields.
2. **Empty and duplicated reviews** (same `review_body`) are removed.
3. **Label** (see decision D-002): 1–2 stars → `Bad`, 3 stars → `Neutral`, 4–5 stars → `Good`.
4. **Hold-out set.** The official `test` split is kept apart and never shown to Neural Designer. It is used later to
   check that the deployed model (OpenNN) gives the same results as in Neural Designer. Training reviews whose text
   also appears in the hold-out set are removed to avoid leakage.
5. **Balanced sample.** From the `train` + `validation` pool (202,980 reviews after steps 1–4), a random sample of
   10,000 reviews per class is drawn (seed 42) and shuffled. `Neutral` comes from a single star level, so it is the
   smallest class in the pool (40,725) and caps `--per-class`. Neural Designer then splits this file into its own
   training, selection and testing subsets.

## Resulting files

| File | Reviews | Bad | Neutral | Good | Use |
|---|---|---|---|---|---|
| `reviews_es_train.csv` | 30,000 | 10,000 | 10,000 | 10,000 | Imported in Neural Designer |
| `reviews_es_holdout.csv` | 4,993 | 1,998 | 1,000 | 1,995 | Final check of the deployed model |

- The hold-out set keeps the distribution of the official test split (20% per star), so it is not balanced across
  the three classes.
- Review length (`review_body`): median 22 words, 95% of reviews under 73 words, longest 506.
- In OpenNN tokens (words and punctuation marks, plus 3 control tokens): median 28, and 98.6% of reviews fit in 128.
- Vocabulary of `review_body`: 24,923 distinct tokens, of which 14,429 appear at least twice.
- Every one of the 30 product categories is represented. The largest are `home` and `wireless` (13% each),
  `sports` and `toy` (7% each).

Format: plain ASCII text (therefore also valid UTF-8), tab-separated, one header row, one review per line.

```
review_id  product_id  reviewer_id  product_category  stars  review_title  review_body  sentiment
```

## Column roles in Neural Designer

| Column | Role | Why |
|---|---|---|
| `review_id` | Sample ID | Identifies the review and allows tracing predictions back |
| `product_id`, `reviewer_id` | Unused | Identifiers: the model would memorise them instead of learning from the text |
| `product_category` | Unused | Reviews of a real business will not have an Amazon category. Kept to analyse errors per category |
| `stars` | **Unused** | **Data leakage:** the target is computed from the stars, so using them as input gives a perfect but useless model |
| `review_title` | Unused | Google reviews and social media posts have no title, so the model must not depend on it |
| `review_body` | Input | The text the model learns from |
| `sentiment` | Target | `Good` / `Neutral` / `Bad` |

By default Neural Designer marks the first column as the ID, the last one as the target and **every other column
as an input**, so `stars` and the other metadata columns must be switched to *Unused* before training.
