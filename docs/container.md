# Контейнер API (ЛР6)

Образ `mlops-housing-price:lr6-<short-sha>` содержит HTTP API (`src/housing_price/api.py`) и модель,
обученную во время сборки. Порт контейнера — 8080.

| Endpoint | Ответ | Назначение |
|---|---|---|
| `GET /healthz` | 200 `{"status": "ok"}` | процесс отвечает |
| `GET /readyz` | 200 `{"status": "ready", "model_version": ...}` или 503 | bundle модели загружен и прошел `load_bundle` |
| `POST /predict` | 200 `{"predicted_value", "model_version", "request_id"}`; 422 или 503 | прогноз `median_house_value` для одного района |

Healthcheck образа и Compose проверяет `/readyz`. Контейнер без модели не становится `healthy`.

## Адаптация задания

| В задании | У нас |
|---|---|
| `mlops-flight-delay:lr6-<short-sha>` | `mlops-housing-price:lr6-<short-sha>` |
| `delay_probability` в `[0, 1]` | `predicted_value`: конечное положительное число, доллары США |
| запрос `dep_hour`, `is_weekend` | 9 признаков из `FEATURES`, границы из `data/contract.json`; `total_bedrooms` может быть `null` |
| обучение на учебном образце | обучение на полном наборе (20 640 строк), его SHA-256 проверяется в сборке |

## Подготовка

1. Docker Desktop с Compose v2: `docker version`, `docker compose version`.
2. Полный набор: `dvc update data/raw/housing.csv.dvc`. Если raw.githubusercontent.com недоступен — обходной путь в [README](../README.md#пайплайн-данных-dvc).
   Без файла `data/raw/housing.csv` сборка падает на `COPY`, с другим файлом — на `sha256sum --check`.

## Стадии сборки

| Стадия | Содержимое | Что проверяет |
|---|---|---|
| `quality` | `pyproject.toml`, полный набор, контракт, образец, `src`, `tests`, `scripts`, `Dockerfile`, `compose.yaml`; зависимости `dev` и `tracking` | SHA-256 набора, Ruff, pytest, контракт данных на полном наборе, обучение `random_forest`, seed 42 (MAE 33411.2) |
| `runtime` | runtime-зависимости, wheel пакета, `models/model.joblib` | ничего не собирает; процесс от `10001:10001`, healthcheck по `/readyz` |

- Runtime берет модель и wheel только из `quality`. Если упала любая проверка, модели и wheel нет, runtime-образ не создается.
- Wheel ставится через `RUN --mount=type=bind`: он не остается отдельным слоем образа.
- Модель принадлежит root (`-rw-r--r-- 0 0`): процесс может ее читать, но не может изменить.

## Сборка и запуск

Linux или macOS:

```bash
export SHORT_SHA=$(git rev-parse --short HEAD)
export IMAGE_TAG=lr6-$SHORT_SHA SOURCE_COMMIT=$(git rev-parse HEAD)
docker build --pull --build-arg SOURCE_COMMIT=$SOURCE_COMMIT --tag mlops-housing-price:$IMAGE_TAG .
docker compose up --detach --wait
docker compose ps
docker compose logs --no-color app
```

Windows PowerShell:

```powershell
$env:IMAGE_TAG = "lr6-$(git rev-parse --short HEAD)"
$env:SOURCE_COMMIT = git rev-parse HEAD
docker build --pull --build-arg SOURCE_COMMIT=$env:SOURCE_COMMIT --tag "mlops-housing-price:$env:IMAGE_TAG" .
docker compose up --detach --wait
docker compose ps
```

- `docker compose up --wait` ждет статуса `healthy` и завершается ошибкой, если он не наступил. Фиксированный `sleep` не нужен.
- Порт хоста меняется через `APP_PORT`, например `APP_PORT=8081`. Порт контейнера всегда 8080.
- Без `IMAGE_TAG` Compose не запускается: `required variable IMAGE_TAG is missing a value`.
- Остановка: `docker compose down`.

## Отчет inspect

```bash
python scripts/container_inspect.py --output reports/container/lr6-inspect.txt
```

Скрипт берет образ `mlops-housing-price:lr6-<short-sha HEAD>` и сохраняет:

- image ID, размер, пользователя и healthcheck;
- метку `org.opencontainers.image.revision`;
- содержимое `/app`.

Скрипт завершается с кодом 1, если найдено хотя бы одно из нарушений:

- процесс работает от root;
- healthcheck не проверяет `/readyz`;
- метка revision не совпадает с commit;
- в `/app` есть лишние файлы.

## Связь образа с commit

- Tag `lr6-<short-sha>` и метка `org.opencontainers.image.revision` указывают на commit.
- Image ID — хэш содержимого образа. Одинаковые слои дают тот же ID.
- `latest` не принимается: он указывает на последнюю сборку, какой бы она ни была. По нему нельзя понять, из какого кода собран образ.
- Отчеты из `reports/` не попадают в build context, поэтому commit с отчетами не меняет слои образа.

## Кэш слоев

Проверено на этой ветке:

| Изменение | Перестроено | Из кэша |
|---|---|---|
| нет | 0 шагов | все 21 шаг `CACHED` |
| только `README.md` | `COPY README.md`, `pip wheel`, установка wheel в runtime | зависимости, проверка SHA-256, тесты и обучение, модель |
| `src/` | от `COPY src` до конца `quality`: тесты и обучение заново; установка wheel в runtime | зависимости обеих стадий; `COPY` модели в runtime — обучение дало тот же файл |
| `pyproject.toml` | почти все | базовый образ, пользователь `app` |

Зависимости ставятся до копирования кода: правка кода не запускает повторную установку пакетов.

## Отрицательный сценарий: тест блокирует сборку

Дефект: в незакоммиченной копии добавлен тест `assert 1 == 2`. Затем выполнена сборка `docker build --tag mlops-housing-price:lr6-defect .`.

```text
#19 11.51 FAILED tests/api/test_defect.py::test_defect_injection_blocks_build - Asserti...
#19 11.51 1 failed, 229 passed, 1 warning in 10.47s
ERROR: failed to build: failed to solve: process "/bin/sh -c python -m ruff check src tests scripts ..." did not complete successfully: exit code: 1
$ docker image inspect mlops-housing-price:lr6-defect
Error response from daemon: No such image: mlops-housing-price:lr6-defect
```

Тест удален, сборка снова проходит. Дефект в принимаемую версию не входит.

## Части участников

- Ограничения runtime в Compose, `.dockerignore`, таблица «риск — ограничение — проверка» — @icy07, [#53](https://github.com/haiksarg/T26_MLOps/issues/53).
- Готовность `/readyz` и перенос модели — @NGHtCONTROLA, [#52](https://github.com/haiksarg/T26_MLOps/issues/52).
- Smoke test `scripts/container_smoke.py` и `reports/container/lr6-smoke.json` — @Sheremgato, [#54](https://github.com/haiksarg/T26_MLOps/issues/54).
