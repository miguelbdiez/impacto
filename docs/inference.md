# Inference with OpenNN

The model is trained in Neural Designer and runs in production with OpenNN, without the Neural Designer engine.
Decision D-015 has the full story and the validation results.

```
models/impacto_model_c.nd ──training/export_model.py──▶ models/model_c/
                                                          model.json       network (OpenNN JSON)
                                                          model.bin        parameters (OpenNN binary)
                                                          vocabulary.txt   tokenizer vocabulary
                                                          model_info.json  sequence length, labels, threshold

review text ──normalize_text──▶ impacto_predict (C++, OpenNN, CPU) ──▶ probability of "good"
             (src/impacto/text.py)   (inference/predict.cpp)
```

## 1. Export the model

```bash
uv run --group analysis training/export_model.py models/impacto_model_c.nd models/model_c --threshold 0.44
```

The decision threshold (0.44) is the probability of "good" from which a review is classified as good. It balances
both classes and reproduces Neural Designer's results (D-015).

## 2. Build the predictor

Requires CMake ≥ 3.24 and a C++20 compiler (Visual Studio 2022+ on Windows, recent GCC or Clang on Linux). OpenNN is compiled from source, CPU only. The build takes several minutes the first time.

```bash
# Windows (Visual Studio)
cmake -S inference -B build/inference
cmake --build build/inference --config Release --target impacto_predict --parallel

# Linux
cmake -S inference -B build/inference -DCMAKE_BUILD_TYPE=Release
cmake --build build/inference --target impacto_predict --parallel
```

By default CMake downloads OpenNN from GitHub at the pinned commit (`OPENNN_GIT_TAG` in `inference/CMakeLists.txt`).
To use a local checkout instead, add `-DOPENNN_SOURCE_DIR=<path to opennn>`. It must be the same OpenNN version
Neural Designer used for training: the parameter file stores a fingerprint of the network layout.

## 3. Predict

From Python, as the application does:

```python
from impacto.model import SentimentModel

model = SentimentModel()                       # models/model_c and build/inference by default
model.predict_proba(["Muy buena calidad, lo recomiendo"])   # [0.997...]
model.predict(["No funciona, se rompió a los dos días"])     # ['Bad']
model.predict([""])                                          # [None]: no words to judge
```

From the command line, with texts already normalised, one per line:

```bash
printf 'Muy buena calidad, lo recomiendo\n' | build/inference/Release/impacto_predict models/model_c 128
```

## 4. Checks

```bash
# Accuracy on the hold-out set (never seen by Neural Designer or OpenNN)
uv run --group analysis training/evaluate_inference.py

# Same results as Neural Designer on the project's testing subset
uv run --group analysis training/check_parity.py models/impacto_model_c.nd data/processed_40k/reviews_es_train.csv
```
