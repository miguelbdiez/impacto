# Neural Designer project

The Neural Designer project (`impacto.nd`) is **not in the repository**: its reports include a preview of the
training data, and the dataset licence does not allow redistributing it (see `docs/dataset.md`). The file is
git-ignored. To work on another computer, copy it by other means or recreate it with the steps below.

## Recreating the project

Current configuration: model 2 plus the changes proposed in D-009 / D-010.

1. **Generate the data:** `uv run training/download_dataset.py` and `uv run training/prepare_dataset.py`
   (check the checksums in `docs/dataset.md`).
2. **New project:** text classification, saved as `impacto.nd` in the repository root.
3. **Data source:** `data/processed/reviews_es_train.csv`. Separator: tab. Header: yes. Sample IDs: yes.
4. **Column roles:** only `review_body` as input and `sentiment` as target. Every other column is *Unused*
   (full table and reasons in `docs/dataset.md`).
5. **Text settings:** input sequence length 128, maximum vocabulary 20,000, minimum token frequency 2.
6. **Network:**
   - Embedding: 64 dimensions, scaled, sinusoidal positional encoding.
   - Multi-head attention: 1 layer, 4 heads.
   - Sequence pooling: average.
   - Dense: 64 neurons, ReLU.
   - Classification layer: softmax, 3 outputs.
7. **Training strategy:**
   - Loss: cross-entropy, L2 regularisation 0.001.
   - Optimiser: Adam, learning rate 0.001, batch size 64.
   - Maximum validation failures 10, maximum 75 epochs. Hardware: NVIDIA CUDA.
   - Do not run model selection (growing inputs / neurons).
8. Train, run the testing analysis (confusion matrix) and **save**.

## Checking a saved project

```bash
uv run --group analysis training/inspect_nd.py impacto.nd
uv run --group analysis training/inspect_nd.py impacto.nd --results training/results/model3.json
```

The script reads the `.nd` file without opening Neural Designer. It prints:
- the column roles;
- the text settings and the most frequent tokens of the vocabulary;
- the layers and the training settings;
- the results of the last training (error history, confusion matrix, recall and precision per class).

With `--results` it also saves them as JSON in `training/results/`.

What to check after saving:
- Column roles: only `review_body` is `Input`.
- The vocabulary has no tokens from other columns (`_`, `es`, `product`, `reviewer`).
- The training settings are the ones set in the interface (see the issues noted in D-009).

## File format

A `.nd` file is an HDF5 container whose `files/` group holds:

| File | Content |
|---|---|
| `<name>.ndm` | Model configuration (JSON): data source, column roles, tokenizer and vocabulary, network, training strategy |
| `<name>.ndo` | Report (JSON): one entry per task run (dataset report, training with error history, confusion matrix…) |
| `<name>_<data>_Network.json` | Network definition |
| `<name>_<data>_Params.bin` | Trained parameters |
