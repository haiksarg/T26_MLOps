# housing-price

Учебный MLOps-проект команды №4 курса «Управление процессами машинного обучения (MLOps)»:
прогнозирование стоимости жилья (тема 1 — Housing Price Prediction).

## Структура

- `src/housing_price/` — Python-пакет проекта (метрики качества, точка входа CLI).
- `tests/` — тесты pytest.
- `data/` — локальные данные, в Git не коммитятся (см. `data/README.md`).
- `docs/` — документация команды.
- `.github/workflows/ci.yml` — CI: проверка данных, Ruff, pytest и smoke-запуск `python -m housing_price`.

## Требования

- Git
- Python 3.12 (версия зафиксирована в `.python-version`)

## Установка

Клонирование:

```bash
git clone https://github.com/haiksarg/T26_MLOps.git
cd T26_MLOps
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[dev,data,tracking]"
```

Linux или macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[dev,data,tracking]"
```

Команда `python --version` должна показать `Python 3.12.x`. Если версия другая,
окружение создано не тем интерпретатором: удалите `.venv` и создайте заново.

## Проверки

```bash
python -m ruff check .
python -m pytest -q
```

Ожидаемый вывод:

```text
All checks passed!
... passed
```

## Запуск

```bash
python -m housing_price
housing-price --version
```

Ожидаемый вывод (версия Python может отличаться):

```text
housing-price 0.1.0 | Python 3.12.10
smoke check: RMSE=11902.4, MAE=11666.7
housing-price 0.1.0
```

## Данные

- `data/housing_sample.csv` — разрешенный учебный образец California Housing (40 строк).
  Происхождение и команда пересборки — [data/README.md](data/README.md).
- `data/contract.json` — машинный контракт: поля, роли, типы, пропуски, диапазоны, категории.
- [docs/data-card.md](docs/data-card.md) — карточка набора: назначение, лицензия, ограничения, разделение.

В Git не добавляются полный набор (`data/raw/`), производные данные (`data/processed/`),
отчеты валидации (`reports/`), персональные данные, секреты и выгрузки неизвестного происхождения.
Отчеты воспроизводятся командой проверки данных и сохраняются как артефакт CI.

Версия контракта (`contract_version`) меняется осознанно:

| Изменение                                                              | Версия                 | Пример                                             |
| ---------------------------------------------------------------------- | ---------------------- | -------------------------------------------------- |
| Описание без изменения проверки                                        | patch: `1.0.0 → 1.0.1` | уточнен текст `description`                        |
| Совместимое добавление необязательного поля                            | minor: `1.0.0 → 1.1.0` | новый столбец с `"nullable": true`                 |
| Удаление или переименование поля, изменение типа, смысла или диапазона | major: `1.0.0 → 2.0.0` | `median_house_value` перестал обрезаться на 500001 |

## Проверка данных

Валидатор `src/housing_price/validate_data.py` проверяет CSV по контракту `data/contract.json`
и записывает JSON-отчет с версией контракта, SHA-256 файла, числом строк и результатом каждого правила.

Bash (Linux, macOS):

```bash
python -m housing_price.validate_data --data data/housing_sample.csv --contract data/contract.json --report reports/validation/lr2.json
echo $?
```

PowerShell (одной строкой):

```powershell
python -m housing_price.validate_data --data data/housing_sample.csv --contract data/contract.json --report reports/validation/lr2.json; echo $LASTEXITCODE
```

Коды завершения:

| Код | Значение                                                                                                  |
| --- | --------------------------------------------------------------------------------------------------------- |
| 0   | все проверки пройдены, в отчете `"passed": true`                                                          |
| 1   | нарушение данных: отчет записан с `"passed": false`, неуспешные правила выведены в stderr                 |
| 2   | ошибка запуска: нет файла, поврежденный JSON, в контракте нет `contract_version`, `dataset` или `columns` |

Ожидаемый вывод для образца (код 0):

```text
проверка пройдена: правил: 33, sha256=e11e3d0baa7263ed5e5407f5f3ad5c398b07c49d739bc816953fa958bee146f0
```

Отчет лежит в `reports/validation/lr2.json` и в Git не коммитится. В CI он сохраняется артефактом:
Actions → нужный запуск → Artifacts → `validation-report`.

## Пайплайн данных (DVC)

Команды выполняются в активированном окружении `.venv`: DVC устанавливается вместе с `.[data]`,
а стадии запускают `python` из этого окружения.

**1. Полный набор.** В Git хранится только `data/raw/housing.csv.dvc`: ссылка на источник
и контрольная сумма файла (`dvc import-url`). Удаленного хранилища DVC нет — источник публичный,
и DVC сам скачивает файл по ссылке:

```bash
dvc update data/raw/housing.csv.dvc
git diff --exit-code data/raw/housing.csv.dvc
```

Если источник изменился, `dvc update` перепишет контрольную сумму в `.dvc`-файле, и `git diff`
покажет это (код `1`) — тогда дальше не продолжайте. Предупреждение `stage ... is frozen` ожидаемо:
стадия импорта заморожена, поэтому `dvc repro` не скачивает файл заново и работает без сети.

Если `raw.githubusercontent.com` недоступен и `dvc update` падает с ошибкой сети, скачайте тот же файл
через API GitHub и передайте его DVC:

```bash
python -c "import urllib.request as u; r = u.Request('https://api.github.com/repos/ageron/handson-ml2/contents/datasets/housing/housing.csv?ref=aa555aa16b9d0af6c84e67c7757f3317d05acb12', headers={'Accept': 'application/vnd.github.raw'}); open('data/raw/housing.csv', 'wb').write(u.urlopen(r).read())"
dvc commit -f data/raw/housing.csv.dvc
git diff --exit-code data/raw/housing.csv.dvc
```

`dvc commit` пересчитывает контрольную сумму: если файл тот же, `.dvc`-файл не меняется и `git diff` молчит.

**2. Запуск и проверка.**

```bash
dvc repro
dvc dag
dvc status
dvc params show
```

`dvc repro` выполняет только стадии, у которых изменились зависимости или параметры.
После запуска `dvc status` должен ответить `Data and pipelines are up to date.`

| Стадия       | Что делает                                                                                        | Результат                                           | Владелец    |
| ------------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ----------- |
| `validate`   | проверяет полный набор контрактом `data/contract.json`; при нарушении `dvc repro` останавливается | `reports/validation/raw.json`                       | @haiksarg   |
| `split`      | стратифицированное разделение train/test (`params.yaml` → `split`)                                | `data/split/`                                       | @Sheremgato |
| `preprocess` | заполнение пропусков, кодирование, масштабирование — обучаются только на train                    | `data/processed/`, `models/`                        | @icy07      |
| `train`      | обучение принятой конфигурации (`params.yaml` → `train`) без MLflow                               | `models/model.joblib`, `reports/train_metrics.json` | @haiksarg   |

Разделение выполняется **до** предобработки: так статистики масштабирования и словарь категорий
вычисляются только по train и не «подсматривают» в test (`docs/data-card.md`, раздел 8).

**3. Изменение параметров.** Измените значение в `params.yaml` (например, `split.test_size`):
`dvc status` покажет затронутые стадии, `dvc repro` перезапустит только их,
`dvc params diff` сравнит параметры с зафиксированными в `dvc.lock`.

Результаты стадий (`reports/`, `data/split/`, `data/processed/`, `models/`) в Git не коммитятся:
их воспроизводит `dvc repro`, а `dvc.lock` фиксирует контрольные суммы входов и выходов.

## Эксперименты MLflow (ЛР4)

План эксперимента, основная метрика и точка отсчета — в `docs/adr/0002-metric-and-baseline.md`.
Запуски хранятся в локальной базе SQLite `mlflow.db`; она и артефакты (`mlruns/`, `mlartifacts/`)
в Git не коммитятся.

```bash
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
dvc repro validate
python -m housing_price.train --mlflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

В PowerShell: `$env:MLFLOW_TRACKING_URI="sqlite:///mlflow.db"`. Интерфейс — http://127.0.0.1:5000.

- Фактор эксперимента (`train.model`) и `train.seed` меняются **только в `params.yaml`**, код между
  запусками не правится; после серии запусков `git checkout params.yaml` и `dvc repro` возвращают
  принятую конфигурацию.
- `train.seed` задает разбиение train/test и случайность модели; run называется `<model>-seed<seed>`.
- Каждый run хранит параметры, метрики (`mae`, `rmse`, точку отсчета `baseline_mae`, `mae_skill`),
  теги `git_commit`, `git_dirty`, `data_sha256`, `dvc_md5`, `contract_version`, `seed`, `model`
  и модель (pipeline предобработки + регрессор) с сигнатурой.
- Модель сохраняется в формате skops; типы, которым skops не доверяет, разрешаются явно списком
  `SKOPS_TRUSTED_TYPES` в `src/housing_price/models.py` после проверки, а не переходом на pickle.
- `reports/run.json` хранит идентификатор последнего run — к нему привязывается решение о выпуске в ЛР5.

## Сравнение запусков (ЛР4)

Сравнение выполнено по плану [ADR 0002](docs/adr/0002-metric-and-baseline.md): основная метрика — MAE на test в USD (меньше — лучше), точка отсчета — `median_baseline`. Фактор — только `train.model`; seed `42, 7, 13, 21, 99` задают разбиение train/test и случайность модели. Данные одной версии: `data_sha256` `8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e`. Серия: 3 модели × 5 seed = **15 запусков**, дополнительных попыток не было.

Запуск и сравнение:

```bash
python -m housing_price.run_experiment --seeds 42 7 13 21 99 --models median_baseline linear_regression random_forest
python -m housing_price.compare_runs --experiment housing-price
```

σ — выборочное стандартное отклонение MAE по пяти seed (ddof=1). `mae_skill = 1 − mae / baseline_mae`.

| Вариант           |   n | MAE среднее ± σ | Baseline MAE (среднее) | mae_skill |
| ----------------- | --: | --------------: | ---------------------: | --------: |
| random_forest     |   5 | 33767.4 ± 253.7 |                88635.1 |    0.6190 |
| linear_regression |   5 | 50026.1 ± 337.7 |                88635.1 |    0.4356 |
| median_baseline   |   5 | 88635.1 ± 892.7 |                88635.1 |    0.0000 |

Попарные сравнения по критерию 2σ (разница значима, если `|Δ| > 2·max(σ1, σ2)`):

| Сравнение                                                         | Разница средних MAE | Порог 2σ | Вывод                            |
| ----------------------------------------------------------------- | ------------------: | -------: | -------------------------------- |
| random_forest против median_baseline                              |            +54867.7 |   1785.5 | значимо: random_forest лучше     |
| linear_regression против median_baseline                          |            +38608.9 |   1785.5 | значимо: linear_regression лучше |
| random_forest против linear_regression (лучший против следующего) |            +16258.7 |    675.4 | значимо: random_forest лучше     |

**Вывод.** Обе модели устойчиво лучше baseline, а `random_forest` — лучше линейной регрессии: разницы многократно превышают порог 2σ. Лучший запуск — `random_forest-seed42`, MAE 33411.2.

**Кандидат для ЛР5:** `random_forest` с `rf_n_estimators: 100`, `rf_max_depth: 12`, `seed: 42` (записан в `params.yaml`).

**Ограничения.** Критерий 2σ при пяти seed — учебное правило, а не доказательство статистической значимости. Гиперпараметры не подбирались. Сравнение выполнено по test, поэтому оценка выбранной модели не является независимой. Данные — районы Калифорнии 1990 года с верхним ограничением цены 500001 USD; случайное разбиение не доказывает переносимость на другие годы и регионы.

**Воспроизводимость между ОС.** Метрики лучшего запуска совпадают на Windows и macOS: файл
`reports/train_metrics.json` идентичен байт в байт. Сам файл модели `models/model.joblib` на этих ОС
различается, поэтому на другой ОС `dvc repro` меняет в `dvc.lock` его MD5 и размер; причина пока не установлена.
Модель сравнивается по метрикам, а не по контрольной сумме файла. Изменение этих двух строк в `dvc.lock` не коммитьте.

## Тесты (ЛР5)

Слои тестов, таблица рисков и отрицательный отчет — [docs/testing.md](docs/testing.md).

## Документация

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ADR 0001](docs/adr/0001-project-boundaries.md)
- [Роли команды](docs/team-roles.md)
