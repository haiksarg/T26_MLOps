# Тесты проекта (ЛР5)

## Слои

| Слой | Каталог | Что проверяет |
|---|---|---|
| Unit и contract: данные | `tests/data/` | правила контракта, образец, разделение, утечка, предобработка |
| Unit: оценка | `tests/evaluation/` | метрики, их предусловия, сравнение запусков |
| Model | `tests/model/` | модели, bundle, детерминированность, журналирование в MLflow |
| API | `tests/api/` | внешний интерфейс; сейчас это CLI, HTTP API появится в ЛР7 |
| Integration | `tests/pipeline/` | связка `validate -> train -> load -> predict` |

Общие fixtures находятся в `tests/conftest.py`. Тесты не обращаются к сети и не зависят от порядка запуска,
временные файлы создаются в `tmp_path`, эталонный `data/housing_sample.csv` не меняется.

## Запуск

```bash
python -m pytest -q
python -m pytest -q tests/pipeline
python -m pytest -q tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract
python -m pytest -q --junitxml=reports/tests/lr5-pass.xml
```

Отчет `reports/tests/lr5-pass.xml` в Git не хранится: CI сохраняет его как артефакт `test-report`,
а для принятой версии он приложен к GitHub Release `lr5-v1`.

Исходное состояние перед ЛР5: 97 тестов прошли, упавших нет. После ЛР5: 171 тест.

## Адаптация задания

Задание ЛР5 написано для бинарной классификации рейсов, наш проект — регрессия стоимости жилья (ADR 0002).

| В задании | У нас |
|---|---|
| `predict_proba`, вероятность в `[0, 1]`, форма `(1, 2)` | `predict`, конечное число, форма `(1,)` |
| ROC AUC, отказ при одном классе | MAE, RMSE, отказ при постоянной цели: `mae_skill` не определен |
| порог `>= 15`, хронологическое разбиение | цель без порога, стратифицированное разбиение по `train.seed` |
| `DepHour`, `IsWeekend`, `FlightDate` | правила `data/contract.json` |

## Риски

| Риск | Тест | Ожидаемый сигнал |
|---|---|---|
| обучение на данных, не прошедших контракт | `tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract` | `train` возвращает код 2, модели нет |
| данные изменились после проверки | `tests/pipeline/test_smoke.py::test_train_refuses_data_changed_after_validation` | `train` возвращает код 2, модели нет |
| этапы pipeline несовместимы между собой | `tests/pipeline/test_smoke.py::test_validate_train_load_predict` | падает один из шагов или форма предсказания |
| цель попала в признаки | `tests/data/test_leakage.py::test_target_not_in_features` | assertion о составе `FEATURES` |
| порядок признаков в модели изменился | `tests/model/test_bundle.py::test_bundle_features_match_features_including_order` | assertion о списке `features` |
| файл модели поврежден или чужого формата | `tests/model/test_bundle.py::test_load_bundle_rejects_unusable_file` | `BundleError` вместо сбоя при predict |
| обучение невоспроизводимо при том же seed | `tests/model/test_bundle.py::test_same_seed_gives_same_metrics_and_predictions_for_random_forest` | расхождение метрик или предсказаний |
| метрика считается по `NaN` или бесконечности | `tests/evaluation/test_metric_preconditions.py::test_metrics_reject_nonfinite_values` | `ValueError` |
| постоянная цель: `mae_skill` не определен (аналог одного класса) | `tests/evaluation/test_metric_preconditions.py::test_evaluate_regression_rejects_constant_target` | `ValueError` вместо `ZeroDivisionError` |

## Отрицательный отчет

Дефект: в `load_validated_data` удалена проверка `report["passed"]`. Заранее названный тест упал, дефект удален,
в принимаемую версию он не входит.

```text
$ python -m pytest -q tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract
    assert run_validate() == 1
>   assert run_train() == 2
E   assert 0 == 2
tests/pipeline/test_smoke.py:63: AssertionError
FAILED tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract
1 failed
```

Причина: валидатор отклонил данные (код 1), но без проверки `passed` обучение завершилось успешно (код 0 вместо 2).
