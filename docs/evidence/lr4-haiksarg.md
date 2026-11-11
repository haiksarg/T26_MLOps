# Evidence card ЛР4 — @haiksarg

## Идентификация

- ФИО, группа, команда и GitHub-логин: Саргсян Айк Андраникович, группа Т26УПМО-Т.МО41, команда №4, [@haiksarg](https://github.com/haiksarg).
- Роль в ЛР4 и отличие от роли в ЛР3: в ЛР4 — журналирование экспериментов в MLflow, baseline и интеграция; в ЛР3 — DVC, параметры пайплайна и стадия `validate`.
- Issue и pull request: [issue #31](https://github.com/haiksarg/T26_MLOps/issues/31), итоговый [PR #34](https://github.com/haiksarg/T26_MLOps/pull/34).

## Личный проверяемый вклад

1. Обучение и запись запуска в MLflow: commit [`853897f`](https://github.com/haiksarg/T26_MLOps/commit/853897f4fb3c47f2223d7f329fc096d0a58c13d9), [`log_to_mlflow`](https://github.com/haiksarg/T26_MLOps/blob/853897f4fb3c47f2223d7f329fc096d0a58c13d9/src/housing_price/train.py#L114). Критерий приемки: run содержит теги версий и модель skops с сигнатурой, модель загружается и повторяет предсказание (`tests/test_train.py`).
2. Baseline и доверенные типы skops: commit [`19adbd4`](https://github.com/haiksarg/T26_MLOps/commit/19adbd4b57d68ee9d3c6e3332b156d3ca3fd49cd), [`PIPELINE_TRUSTED_TYPES`](https://github.com/haiksarg/T26_MLOps/blob/19adbd4b57d68ee9d3c6e3332b156d3ca3fd49cd/src/housing_price/models.py#L18). Критерий приемки: baseline сохраняется в MLflow без перехода на pickle. Стадия `train` в DVC: commit [`5e0d796`](https://github.com/haiksarg/T26_MLOps/commit/5e0d796a192c828d05c5ce3668ba64ffe8fb96e5).
3. Review другого участника: [PR #35](https://github.com/haiksarg/T26_MLOps/pull/35#pullrequestreview-5743862889) — MAE при seed 42 повторены; [PR #37](https://github.com/haiksarg/T26_MLOps/pull/37#pullrequestreview-5769958364) — повторены 15 запусков, найдено различие MD5 `models/model.joblib` между Windows и macOS, различие записано в README.

## MLflow run

- Experiment, run ID и run name: `housing-price`, `4159800f973e49a28d4015cb122d4b4c`, `random_forest-seed42`.
- `git_commit`: `9a7555194848fb2ddc363df12d68fd76bc1cb37d` (`git_dirty=false`); `data_sha256`: `8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e`; `dvc_md5`: `d1c47305887e2252bf1ccbd74ff159a6`; `contract_version`: `1.0.0`.
- Измененный параметр (фактор) и seed: `train.model = random_forest`, `train.seed = 42`.
- Метрики: `mae` 33411.208, `baseline_mae` 88227.466 (точка отсчета), `mae_skill` 0.6213; дополнительно `rmse` 49547.104.
- URI модели: `models:/m-a23e0ed28fa245be9701933b71c0127c`.

## Индивидуальное воспроизведение

- Поиск run: `mlflow.search_runs(experiment_names=["housing-price"], filter_string="tags.model = 'random_forest' and tags.seed = '42'")`.
- Повторный запуск: `python -m housing_price.train --mlflow` при принятой конфигурации: `random_forest-seed42: MAE=33411.2, baseline MAE=88227.5, skill=0.6213`; значение совпадает с запусками @icy07 и @Sheremgato.
- Загрузка модели: `mlflow.sklearn.load_model("models:/m-a23e0ed28fa245be9701933b71c0127c")`; предсказания для первых трех строк `data/split/test.csv`: `485385.76, 261169.23, 222544.38` при фактических ценах `500001, 162500, 204600`.
- Альтернативный run и вывод по 2σ: `linear_regression`; по пяти seed `random_forest` 33767.4 ± 253.7, `linear_regression` 50026.1 ± 337.7; разница 16258.7 больше порога 675.4, поэтому лес признан лучше.

## Инженерное решение и риск

- Выбранное решение и рассмотренная альтернатива: `train.seed` задает и разбиение train/test, и случайность модели. Альтернатива — только случайность модели: тогда у медианы и линейной регрессии разброс по seed был бы нулевым, и критерий 2σ не работал бы для них.
- Основной риск: результат будет связан не с той версией данных или кода, либо модель будет сохранена в формате без проверки типов при загрузке.
- Тег, метрика, тест или артефакт, который обнаруживает проблему: `train.py` отказывает, если SHA-256 файла не совпадает с отчетом `validate`; теги `data_sha256` и `git_dirty`; тесты `test_load_validated_data_*`. При первом сохранении skops отклонил `numpy.dtype`: тип найден через `skops.io.get_untrusted_types`, его хранит `SimpleImputer` (`_fit_dtype`), тип разрешен явно, pickle не использован.

## Использование ИИ

- Использованный инструмент: Claude Code. Он написал код `train.py`, `models.py`, тесты и документацию, выполнил запуски, проверил PR участников и подготовил тексты review. Решения о постановке и распределении работ команды принимал я; review отправлял я.
- Какие фрагменты проверены самостоятельно: результаты review PR #35 и #37 и таблицу сравнения в README перед одобрением и merge; повтор лучшего запуска выполнял Claude Code, независимо его повторил @Sheremgato в review PR #34 (MAE 33411.2).
