# Evidence card ЛР5 — Шереметов Мурат

| Поле | Значение |
|---|---|
| Студент | Шереметов Мурат Олегович, Т26УПМО-Т.МО41, команда №4, GitHub: @Sheremgato |
| Роль | Evaluation test engineer: предусловия и проверка метрик. В ЛР4 — ADR 0002 и варианты моделей; в ЛР5 — отказы на некорректных входах и тесты этих отказов. |
| Задача | [Issue #42: предусловия метрик и отказ при постоянной цели](https://github.com/haiksarg/T26_MLOps/issues/42) |
| Личный артефакт | `tests/evaluation/test_metric_preconditions.py` — 33 тестовых случая; `src/housing_price/metrics.py::evaluate_regression`; подключение функции в `train_and_evaluate`. Коммит кода и тестов: `aa8603f`. Работа и карточка — в [PR #45](https://github.com/haiksarg/T26_MLOps/pull/45). |
| Контролируемый риск | Расчет метрик на пустых данных, разной длине, NaN или бесконечности; деление на ноль при расчете `mae_skill`, когда цель test совпадает с медианой train. |
| Defect injection | Временно удалена проверка `baseline_mae == 0`. Заранее выбранный `tests/evaluation/test_metric_preconditions.py::test_evaluate_regression_rejects_constant_target[perfect]` фактически упал. Дефект удален и не закоммичен. |
| Диагностика | Вместо ожидаемого `ValueError` получен `ZeroDivisionError: float division by zero` в выражении `1 - model_mae / baseline_mae`. Фрагмент traceback приведен ниже. |
| Воспроизведение | Один тест: `python -m pytest -q 'tests/evaluation/test_metric_preconditions.py::test_evaluate_regression_rejects_constant_target[perfect]'`. Весь набор: `python -m pytest -q --junitxml=reports/tests/lr5-pass.xml`. |
| Использование ИИ | ИИ-помощник: код и тесты; проверка — pytest, Ruff, DVC. |

## Что проверяют тесты

- `mae`, `rmse` и `evaluate_regression`: разная длина, пустой вход, NaN и обе бесконечности в каждом из двух входов. Ожидается `ValueError` с проверкой текста через `match`.
- `evaluate_regression`: NaN и бесконечности в `reference`, нулевой `baseline_mae`; отказ проверен как для точного, так и для ошибочного прогноза на постоянной цели.
- Положительные случаи: идеальный прогноз, прогноз baseline и прогноз хуже baseline. Проверяются четыре ключа, значения через `pytest.approx`, `mae >= 0` и `rmse >= mae`.
- `test_train_rejects_constant_target`: общие fixtures `pipeline_frame` и `params`; вся цель заменяется одной константой. Проверяется, что обучение использует новый отказ с `ValueError`.

`reference` — медиана цели **train**, а не статистика test. Отказ в `evaluate_regression` связан именно с `baseline_mae == 0`: в этом случае нормированная метрика `mae_skill` не определена.

## Временный дефект и восстановление

Дефект и тест выбраны до изменения кода: убрать проверку `baseline_mae == 0` и запустить один названный тест.

```bash
python -m pytest -q 'tests/evaluation/test_metric_preconditions.py::test_evaluate_regression_rejects_constant_target[perfect]'
```

Первый полезный фрагмент отрицательного запуска:

```text
with pytest.raises(ValueError, match="baseline_mae.*0.*mae_skill"):
>   evaluate_regression([5.0, 5.0], y_pred, reference=5.0)
...
>   "mae_skill": 1 - model_mae / baseline_mae,
E   ZeroDivisionError: float division by zero
src/housing_price/metrics.py:46: ZeroDivisionError
1 failed
```

Причина: и модель, и baseline предсказывают постоянную цель точно; обе MAE равны нулю. Без предусловия выражение `0 / 0` дает `ZeroDivisionError`, который не удовлетворяет ожиданию `ValueError`.

После `git restore -- src/housing_price/metrics.py` файл совпал с рабочей версией байт в байт. Та же команда дала **1 passed**, затем весь набор — **137 passed**. Временный дефект в историю не вошел.

## Результаты проверки

- До изменений: **104 passed**. После изменений: **137 passed**, в том числе 33 новых случая.
- `python -m ruff check .` — **All checks passed!**
- `dvc repro` — успешно; конфигурация `random_forest`, seed 42, 100 деревьев, глубина 12.
- MAE полного набора: **33411.20807157644** (33411.2), как в ЛР4. `reports/train_metrics.json` совпал по MD5: `87854292b5192c44db10f46bc1bbbe1f`.
- В pytest осталось одно предупреждение MLflow/SQLAlchemy о deprecated `noload`, присутствовавшее и до изменений; упавших тестов нет.
- Локальный JUnit: `reports/tests/lr5-pass.xml`. Workflow проекта сохраняет такой отчет как артефакт `test-report`.
- Изменение `dvc.lock` после воспроизведения восстановлено; `dvc.lock`, данные, модели, отчеты и `mlflow.db` в коммиты не входят.

## Проверка коллеги

Проверен [PR #44 Андрея (@icy07)](https://github.com/haiksarg/T26_MLOps/pull/44) по [issue #41](https://github.com/haiksarg/T26_MLOps/issues/41), коммит `56dfea270f9425efcdc5748533b7cd1224bee114`. Его код и тесты проверялись в отдельной копии, без изменения своей рабочей ветки.

- `python -m pytest -q tests/model/test_bundle.py` — **34 passed**.
- `python -m pytest -q` — **138 passed**, одно прежнее предупреждение MLflow/SQLAlchemy.
- `python -m ruff check .` — **All checks passed!**

Проверены состав и версии bundle, независимая фиксация порядка признаков, отказы загрузки, предсказания после сохранения и повторяемость леса при одном seed. Сравнение с `PINNED_FEATURES` обнаружит перестановку даже при одновременном изменении `FEATURES` и порядка в bundle.

Замечание к проверенному коммиту: в diff только `tests/model/test_bundle.py`, а `docs/evidence/lr5-icy07.md`, заявленной в описании PR, еще нет. До merge нужно добавить карточку в этот же PR.

Опубликовано [review PR #44](https://github.com/haiksarg/T26_MLOps/pull/44#pullrequestreview-5812439909), включая [комментарий к строке 102](https://github.com/haiksarg/T26_MLOps/pull/44#discussion_r4501895894) о независимой фиксации порядка признаков. Review отправлено как **Approve**, с замечанием о необходимости добавить карточку Андрея до merge.
