# Evidence card ЛР4 — @Sheremgato

## Идентификация

- Шереметов Мурат Олегович, группа Т26УПМО-Т.МО41, команда №4, GitHub @Sheremgato.
- Роль ЛР4: план эксперимента и варианты моделей. В ЛР3 отвечал за стадию split.
- Задача: [issue #32](https://github.com/haiksarg/T26_MLOps/issues/32).
- PR: ветка `feat/issue-32-models-adr` в `haiksarg/mourberg`;
  [страница сравнения](https://github.com/haiksarg/T26_MLOps/compare/mourberg...Sheremgato:T26_MLOps:feat/issue-32-models-adr).

## Личный проверяемый вклад

1. [ADR 0002](https://github.com/Sheremgato/T26_MLOps/blob/7346abbcdd519cbea7f7735c8f9417dca6091748/docs/adr/0002-metric-and-baseline.md#L18),
   commit [`7346abb`](https://github.com/Sheremgato/T26_MLOps/commit/7346abbcdd519cbea7f7735c8f9417dca6091748):
   MAE вместо RMSE для эксперимента ЛР4, baseline-медиана, данные, пять seed,
   критерий 2σ и 15 попыток. Настройки леса (100 деревьев, глубина 12) записаны до запусков.
2. [Варианты моделей и доверенные типы](https://github.com/Sheremgato/T26_MLOps/blob/2ccc07c807ee74cd113cdcb9b47773de79465923/src/housing_price/models.py#L21),
   commit [`2ccc07c`](https://github.com/Sheremgato/T26_MLOps/commit/2ccc07c807ee74cd113cdcb9b47773de79465923):
   LinearRegression и RandomForestRegressor; seed передается в лес;
   параметры находятся в YAML, состояние DVC обновлено.
3. [Тесты моделей и skops](https://github.com/Sheremgato/T26_MLOps/blob/83f615549f27e3a7c61560195d1d2b4be3f1bf51/tests/test_models.py#L27),
   commit [`83f6155`](https://github.com/Sheremgato/T26_MLOps/commit/83f615549f27e3a7c61560195d1d2b4be3f1bf51):
   проверяются классы, настройки леса и совпадение предсказаний после загрузки
   трех видов pipeline с явным списком доверенных типов.
4. Проверена часть Айка в [PR #34](https://github.com/haiksarg/T26_MLOps/pull/34):
   в `load_validated_data` обучение отклоняется при `passed=false` и несовпадении SHA-256.
   `python -m pytest -q tests/test_train.py -k load_validated_data` — 3 passed.
   Содержательный комментарий подготовлен, но еще не опубликован;
   прямую ссылку на review нужно добавить после отправки.

## MLflow run

Experiment: `housing-price`. Все три проверочных run завершены, seed — 42.
Baseline MAE для этого разбиения — 88227.46608527131 USD.

| Модель | Run ID | MAE, USD | mae_skill |
|---|---|---:|---:|
| `median_baseline` | `7d07f6797b484714a16ae32439f1db56` | 88227.4661 | 0.000000 |
| `linear_regression` | `3372afac123443ca87f06dba0fc0fb14` | 49775.5957 | 0.435827 |
| `random_forest` | `2a1cc0820f55402e9676447bbb74e54f` | 33411.2081 | 0.621306 |

Личный артефакт для демонстрации — `random_forest-seed42`:

- `git_commit`: `83f615549f27e3a7c61560195d1d2b4be3f1bf51`, `git_dirty`: `false`.
- `data_sha256`: `8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e`.
- `dvc_md5`: `d1c47305887e2252bf1ccbd74ff159a6`, `contract_version`: `1.0.0`.
- Фактор: `train.model=random_forest`; `train.seed=42`;
  `rf_n_estimators=100`, `rf_max_depth=12`.
- URI модели: `models:/m-7f3d042e49ae4709be7187dbc8df467b`; фактический формат — skops.

## Индивидуальное воспроизведение

В активном `.venv` задать `MLFLOW_TRACKING_URI=sqlite:///mlflow.db`.
Поиск: `mlflow.search_runs(experiment_names=["housing-price"])`.
Для повторения леса временно поставить `train.model: random_forest` в `params.yaml`,
выполнить `python -m housing_price.train --mlflow`, затем вернуть `median_baseline`.
Повторное обучение через `train_and_evaluate` дало MAE `33411.20807158` USD.

Загрузка: `mlflow.sklearn.load_model("models:/m-7f3d042e49ae4709be7187dbc8df467b")`.
Загружены все три артефакта, их прогнозы на первых пяти строках соответствующего test
сравнены с заново обученными pipeline (`rtol=1e-12`, `atol=1e-9`): совпадение подтверждено.
Первые прогнозы леса: 485385.7576, 261169.2296, 222544.3780, 179408.0571, 205074.2125 USD.

Альтернатива — baseline из таблицы. Проверки при одном seed показывают работоспособность,
но не дают разброса по пяти seed: вывод по критерию 2σ пока не делается.
Итоговую серию 3 × 5 = 15 и сравнение оформляет @icy07 в issue #33.

Проверки локальной версии: `python -m pytest -q` — **66 passed, 1 warning**
(предупреждение о deprecated API внутри MLflow/SQLAlchemy);
`python -m ruff check .` — **All checks passed**; `dvc repro` и `dvc status` —
пайплайн актуален. После проверок возвращены `median_baseline`, seed 42 и результаты
стадии train для baseline.

## Инженерное решение и риск

Линейная регрессия проверяет простой обучаемый вариант, лес — нелинейные зависимости.
Их настройки зафиксированы до сравнения; дополнительные попытки по результатам test
не добавлялись. MAE интерпретируется как абсолютная ошибка в USD, RMSE сохранена дополнительно.

При первом сохранении леса возникла ожидаемая ошибка
`UntrustedTypesFoundException: sklearn.tree._tree.Tree`.
Неуспешный run `0fc62627c7ee4d8ba760ee494e1722e5` сохранен со статусом FAILED.
Диагностика `skops.io.get_untrusted_types(data=skops.io.dumps(model))` показала:

- baseline и линейная регрессия — `numpy.dtype`;
- лес — `numpy.dtype` и `sklearn.tree._tree.Tree`.

`numpy.dtype` описывает числовой тип в SimpleImputer. `Tree` хранит структуру обученного
леса и разрешен только для наших артефактов: доверие к типу не проверяет содержимое
индексов дерева. Список задан явно, автоматического разрешения всех обнаруженных типов
и перехода на pickle нет. Тесты сохранения/загрузки контролируют этот результат.
Предобработка обучается только на train, а TARGET не входит в FEATURES.
