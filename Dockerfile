# syntax=docker/dockerfile:1
# Образ API стоимости жилья (ЛР6). Две стадии:
#   quality — Ruff, pytest, проверка контракта и обучение модели; любая ошибка останавливает сборку;
#   runtime — только зависимости, пакет и модель; процесс работает от UID/GID 10001.
# Перед сборкой нужен полный набор: dvc update data/raw/housing.csv.dvc (docs/container.md).
#   docker build --pull --tag mlops-housing-price:lr6-$(git rev-parse --short HEAD) .

ARG PYTHON_IMAGE=python:3.12.16-slim-trixie

FROM ${PYTHON_IMAGE} AS quality

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/build/src
WORKDIR /build

# Зависимости ставятся до кода: слой пересобирается только при изменении pyproject.toml.
# Пакет-заглушка позволяет pip прочитать зависимости из pyproject без исходников.
COPY pyproject.toml ./
RUN mkdir -p src/housing_price \
    && touch README.md src/housing_price/__init__.py \
    && python -m pip install ".[dev,tracking]" \
    && python -m pip uninstall --yes housing-price \
    && rm -rf src README.md

# Полный набор должен совпадать с версией в DVC (data/raw/housing.csv.dvc, docs/data-card.md).
COPY data/raw/housing.csv ./data/raw/
RUN echo "8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e  data/raw/housing.csv" \
    | sha256sum --check -

COPY data/README.md data/contract.json data/housing_sample.csv ./data/
COPY params.yaml ./
COPY src ./src
# Тесты слоя container проверяют сами файлы сборки и скрипты из scripts/.
COPY Dockerfile compose.yaml ./
COPY scripts ./scripts
COPY tests ./tests

# Quality gate: при ошибке любой команды runtime-образ не создается.
RUN python -m ruff check src tests scripts \
    && python -m pytest -q -p no:cacheprovider \
    && python -m housing_price.validate_data \
        --data data/raw/housing.csv \
        --contract data/contract.json \
        --report reports/validation/raw.json \
    && python -m housing_price.train --params params.yaml

# README нужен только для метаданных пакета, поэтому копируется после проверок:
# его правка не перезапускает тесты и обучение.
COPY README.md ./
RUN python -m pip wheel --no-deps --wheel-dir /wheels .


FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_PATH=/app/models/model.joblib

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin app
WORKDIR /app

# Только runtime-зависимости из pyproject: без pytest, Ruff, DVC и MLflow.
COPY pyproject.toml /tmp/pkg/
RUN cd /tmp/pkg \
    && mkdir -p src/housing_price \
    && touch README.md src/housing_price/__init__.py \
    && python -m pip install . \
    && python -m pip uninstall --yes housing-price \
    && rm -rf /tmp/pkg

# Модель из quality-стадии: владелец root, процесс может ее только читать.
COPY --from=quality /build/models/model.joblib /app/models/model.joblib

# Пакет ставится из wheel через bind mount: сам wheel не остается слоем образа.
RUN --mount=type=bind,from=quality,source=/wheels,target=/tmp/wheels \
    python -m pip install --no-deps /tmp/wheels/*.whl

ARG SOURCE_COMMIT=unknown
LABEL org.opencontainers.image.title="mlops-housing-price" \
      org.opencontainers.image.source="https://github.com/haiksarg/T26_MLOps" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}"

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=2)"]
CMD ["uvicorn", "housing_price.api:app", "--host", "0.0.0.0", "--port", "8080"]
