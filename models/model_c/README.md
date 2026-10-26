# Model C: Spanish review sentiment (good / bad)

Text classification model trained in [Neural Designer](https://www.neuraldesigner.com) and run with
[OpenNN](https://github.com/Artelnics/opennn) (see `docs/inference.md` and decisions D-014, D-015).

| File | Content |
|---|---|
| `model.json` | Network definition (OpenNN): embedding 20,000 × 64 with positional encoding, average pooling, dense 64 ReLU, sigmoid output |
| `model.bin` | Trained parameters (OpenNN binary format, 1,284,225 values) |
| `vocabulary.txt` | Tokenizer vocabulary, one token per line (the line number is the token id) |
| `model_info.json` | Sequence length (128), labels (`bad`, `good`) and decision threshold (0.44) |

**Input.** Spanish text normalised with `impacto.text.normalize_text` (ASCII, D-008). Output: probability that the
review is good; ≥ 0.44 means good.

**Results.** 88.4% accuracy on Neural Designer's testing subset, 88.5% on 3,993 hold-out Amazon reviews (AUC 0.955),
and 87.1% agreement with the stars on 2,796 real Google reviews of El Corte Inglés Princesa (AUC 0.940).

**Training data and terms of use.** Trained on the Spanish part of the Multilingual Amazon Reviews Corpus
(Keung et al., 2020), 40,000 reviews per class, 1–2 stars as bad and 4–5 stars as good. That corpus may only be used
for non-commercial research, and these weights and vocabulary are derived from it: use this model for
non-commercial purposes only. The data itself is not included in this repository (see `docs/dataset.md`).
