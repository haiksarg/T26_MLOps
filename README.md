# housing-price

Учебный MLOps-проект команды №4 курса «Управление процессами машинного обучения (MLOps)»:
прогнозирование стоимости жилья (тема 1 — Housing Price Prediction).

## Структура

- `src/housing_price/` — Python-пакет проекта (метрики качества, точка входа CLI).
- `tests/` — тесты pytest.
- `data/` — локальные данные, в Git не коммитятся (см. `data/README.md`).
- `docs/` — документация команды.
- `.github/workflows/ci.yml` — CI: Ruff и pytest и smoke-запуск `python -m housing_price`.

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

## Документация

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ADR 0001](docs/adr/0001-project-boundaries.md)
- [Роли команды](docs/team-roles.md)
