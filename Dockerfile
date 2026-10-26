# impacto: Streamlit app + OpenNN predictor (decision D-022). Built and run by docker-compose.yml.

# ---- Stage 1: the OpenNN predictor, compiled from source, CPU only ----------------------------------
# Debian trixie ships GCC 14 and CMake 3.31: OpenNN needs C++20 and CMake >= 3.24.
FROM debian:trixie-slim AS predictor
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY inference/ inference/
# Each OpenNN source file can take over 1 GB to compile: an unlimited --parallel on a many-core machine runs out of
# memory and takes the Docker engine down. Raise BUILD_JOBS (docker compose build --build-arg BUILD_JOBS=8) if
# Docker has plenty of memory.
ARG BUILD_JOBS=4
# CMake downloads OpenNN from GitHub at the commit pinned in inference/CMakeLists.txt
RUN cmake -S inference -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target impacto_predict --parallel ${BUILD_JOBS}

# ---- Stage 2: the app ---------------------------------------------------------------------------------
FROM python:3.13-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    IMPACTO_PREDICT=/app/bin/impacto_predict
# The predictor uses OpenMP at run time
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Dependencies first, so they are cached while the code changes
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-install-project
# Chromium for the free Google Maps search of the "create dashboard" dialog
RUN playwright install --with-deps chromium

COPY src/ src/
RUN uv sync --frozen
COPY app/ app/
COPY pipeline/ pipeline/
COPY scraping/ scraping/
COPY .streamlit/ .streamlit/
COPY models/model_c/ models/model_c/
COPY --from=predictor /src/build/impacto_predict /app/bin/impacto_predict
COPY docker/entrypoint.sh /entrypoint.sh
# A Windows checkout may turn the script's line endings into CRLF, which /bin/sh cannot run
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8501
ENTRYPOINT ["/entrypoint.sh"]
