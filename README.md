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
python -m pip install -e ".[dev]"
```

Linux или macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
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
.........                                                        [100%]
9 passed in 0.03s
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

| Изменение | Версия | Пример |
|---|---|---|
| Описание без изменения проверки | patch: `1.0.0 → 1.0.1` | уточнен текст `description` |
| Совместимое добавление необязательного поля | minor: `1.0.0 → 1.1.0` | новый столбец с `"nullable": true` |
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

| Код | Значение |
|---|---|
| 0 | все проверки пройдены, в отчете `"passed": true` |
| 1 | нарушение данных: отчет записан с `"passed": false`, неуспешные правила выведены в stderr |
| 2 | ошибка запуска: нет файла, поврежденный JSON, в контракте нет `contract_version`, `dataset` или `columns` |

Ожидаемый вывод для образца (код 0):

```text
проверка пройдена: правил: 33, sha256=e11e3d0baa7263ed5e5407f5f3ad5c398b07c49d739bc816953fa958bee146f0
```

Отчет лежит в `reports/validation/lr2.json` и в Git не коммитится. В CI он сохраняется артефактом:
Actions → нужный запуск → Artifacts → `validation-report`.

## Пайплайн данных (DVC)

Команды выполняются в активированном окружении `.venv`: DVC устанавливается вместе с `.[dev]`,
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

| Стадия | Что делает | Результат | Владелец |
|---|---|---|---|
| `validate` | проверяет полный набор контрактом `data/contract.json`; при нарушении `dvc repro` останавливается | `reports/validation/raw.json` | @haiksarg |
| `split` | стратифицированное разделение train/test (`params.yaml` → `split`) | `data/split/` | @Sheremgato |
| `preprocess` | заполнение пропусков, кодирование, масштабирование — обучаются только на train | `data/processed/`, `models/` | @icy07 |

Разделение выполняется **до** предобработки: так статистики масштабирования и словарь категорий
вычисляются только по train и не «подсматривают» в test (`docs/data-card.md`, раздел 8).

**3. Изменение параметров.** Измените значение в `params.yaml` (например, `split.test_size`):
`dvc status` покажет затронутые стадии, `dvc repro` перезапустит только их,
`dvc params diff` сравнит параметры с зафиксированными в `dvc.lock`.

Результаты стадий (`reports/`, `data/split/`, `data/processed/`, `models/`) в Git не коммитятся:
их воспроизводит `dvc repro`, а `dvc.lock` фиксирует контрольные суммы входов и выходов.

## Документация

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ADR 0001](docs/adr/0001-project-boundaries.md)
- [Роли команды](docs/team-roles.md)
