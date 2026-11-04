# Evidence card ЛР4 — @icy07

## Идентификация

- ФИО, группа, команда и GitHub-логин: Ильин Андрей Александрович, группа Т26УПМО-Т.МО41, команда №4, [@icy07](https://github.com/icy07).
- Роль в ЛР4 и отличие от роли в ЛР3: в ЛР4 — запуски и сравнение (серия из 15 запусков, сравнение с учетом разброса, принятая конфигурация); в ЛР3 — стадия `preprocess` DVC-пайплайна.
- Issue и pull request: [issue #33](https://github.com/haiksarg/T26_MLOps/issues/33), [PR #37](https://github.com/haiksarg/T26_MLOps/pull/37).

## Личный проверяемый вклад

1. Серия запусков: `run_experiment.py` меняет только `train.model` и `train.seed` в `params.yaml`, вызывает `train --mlflow` и в `finally` возвращает файл байт в байт. Commit [`08beac6`](https://github.com/haiksarg/T26_MLOps/commit/08beac6), [run_experiment.py#L37-L50](https://github.com/haiksarg/T26_MLOps/blob/08beac6/src/housing_price/run_experiment.py#L37-L50) (замена значений без перезаписи YAML) и [#L53-L82](https://github.com/haiksarg/T26_MLOps/blob/08beac6/src/housing_price/run_experiment.py#L53-L82) (серия и восстановление). Критерий приемки: после серии и после сбоя запуска `params.yaml` не отличается от исходного, в том числе с CRLF — тесты [`test_run_series_restores_crlf_params_byte_for_byte`](https://github.com/haiksarg/T26_MLOps/blob/08beac6/tests/test_compare_runs.py#L94) и [`test_run_series_restores_params_when_runner_raises`](https://github.com/haiksarg/T26_MLOps/blob/08beac6/tests/test_compare_runs.py#L120).
2. Сравнение запусков: `compare_runs.py` читает запуски через `mlflow.search_runs`, отказывает при разных `data_sha256` и применяет критерий `|Δ| > 2·max(σ1, σ2)`. Commit [`08beac6`](https://github.com/haiksarg/T26_MLOps/commit/08beac6), [compare_runs.py#L80-L105](https://github.com/haiksarg/T26_MLOps/blob/08beac6/src/housing_price/compare_runs.py#L80-L105) (проверка версии данных) и [#L121-L128](https://github.com/haiksarg/T26_MLOps/blob/08beac6/src/housing_price/compare_runs.py#L121-L128) (критерий 2σ). Критерий приемки: при смешении версий данных выход с кодом 1, граница ровно 2σ не считается значимой — тесты [`test_check_runs_refuses_different_data_versions`](https://github.com/haiksarg/T26_MLOps/blob/08beac6/tests/test_compare_runs.py#L288) и [`test_difference_larger_than_two_sigma_is_significant`](https://github.com/haiksarg/T26_MLOps/blob/08beac6/tests/test_compare_runs.py#L199). Локально: `ruff check .` — чисто, `pytest -q` — 90 passed.
3. README и принятая конфигурация: раздел «Сравнение запусков (ЛР4)» и `train.model: random_forest` (`seed: 42`) в `params.yaml`, `dvc repro`, обновленный `dvc.lock`. Commit [`c3454a6`](https://github.com/haiksarg/T26_MLOps/commit/c3454a6). Критерий приемки: таблица README совпадает с выводом `compare_runs`, а `dvc.lock` изменился только из-за `params.yaml`.
4. Review другого участника: [review PR #35](https://github.com/haiksarg/T26_MLOps/pull/35#pullrequestreview-5685775609) (ADR 0002 и модели Мурата, автор @Sheremgato). Проверка `assert set(untrusted) <= set(SKOPS_TRUSTED_TYPES[kind])` в [tests/test_models.py#L61](https://github.com/haiksarg/T26_MLOps/blob/83f6155/tests/test_models.py#L61) односторонняя: она не поймает лишний тип в списке доверенных. Предложил для `linear_regression` и `median_baseline` проверять равенство множеств, а для леса — что `sklearn.tree._tree.Tree` действительно есть среди недоверенных типов, иначе исключение в списке ничем не подтверждено.

## MLflow run

- Experiment, run ID и run name: `housing-price`, `356c36dc5b0d42df9ae112c863a0d951`, `random_forest-seed42` (лучший запуск серии по MAE).
- `git_commit`: `22c777d37dc47bd786342e8aa7e58ee212c438b4` (`git_dirty=false`); `data_sha256`: `8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e`; `dvc_md5`: `d1c47305887e2252bf1ccbd74ff159a6`; `contract_version`: `1.0.0`.
- Измененный параметр (фактор) и seed: `train.model = random_forest`, `seed = 42` (`rf_n_estimators: 100`, `rf_max_depth: 12`, `random_state=seed`).
- Метрики: `mae` 33411.208, `baseline_mae` 88227.466 (точка отсчета, `median_baseline`), `mae_skill` 0.6213; дополнительно `rmse` 49547.104.
- URI модели: `models:/m-20ad7e15833b42b8a68446c8766dee61`.

## Индивидуальное воспроизведение

Поиск run: `mlflow.search_runs(experiment_names=["housing-price"], filter_string="tags.model = 'random_forest' and tags.seed = '42'")` вернул два запуска — исходный `356c36dc…` и повтор `d612f4bc…` — с одинаковым `metrics.mae` 33411.208072 и `git_dirty=false`.

- Повторный запуск: `python -m housing_price.train --mlflow` при принятой конфигурации дал `random_forest-seed42: MAE=33411.2, baseline MAE=88227.5, skill=0.6213`, run `d612f4bc46e64e7ea18234a5da42a5b1`. Повтор не входит в серию из 15 запусков и в сравнение README.
- Загрузка модели: `mlflow.sklearn.load_model("models:/m-20ad7e15833b42b8a68446c8766dee61")`; предсказания для первых трех строк `data/split/test.csv`: `485385.76, 261169.23, 222544.38` при фактических ценах `500001.0, 162500.0, 204600.0`. Первая цена равна верхнему ограничению 500001 USD из ADR 0002.
- Альтернативный run и 2σ: `linear_regression` (run `linear_regression-seed42` `61ad7bd7cac84ba5847fddba1af71b41`, MAE 49775.6). По пяти seed: `random_forest` 33767.4 ± 253.7, `linear_regression` 50026.1 ± 337.7; разница 16258.7 больше порога `2·max(253.7, 337.7) = 675.4`, значит `random_forest` лучше. Против baseline (88635.1 ± 892.7): разница 54867.7 при пороге 1785.5.

## Инженерное решение и риск

- Выбранное решение и рассмотренная альтернатива: значения `train.model` и `train.seed` подставляются в `params.yaml` заменой только самих значений в секции `train`, а исходные байты файла возвращаются в `finally`. Альтернатива — перезаписывать YAML через `yaml.safe_dump`: она теряет комментарии, порядок ключей и окончания строк, а на Windows дала бы изменения `params.yaml` и `dvc.lock` без смысла. Вручную править файл перед каждым из 15 запусков тоже не стали: так легко ошибиться в seed.
- Основной риск: вывод о «лучшей модели» окажется неверным, если запуски выполнены на разных версиях данных или на изменённом рабочем дереве, или если сбой серии оставит измененный `params.yaml`.
- Тег, метрика, тест или артефакт, который обнаруживает проблему: теги `data_sha256` и `git_dirty` у каждого запуска; `compare_runs` завершается с кодом 1 при разных `data_sha256` (`test_check_runs_refuses_different_data_versions`); `params.yaml` после серии проверяется `git status` и тестом `test_run_series_restores_params_when_runner_raises`. Ограничение вывода: критерий 2σ при пяти seed — учебное правило, а сравнение выполнено по test, поэтому оценка выбранной модели не является независимой.

## Использование ИИ

- Использованный инструмент: Claude. Он написал черновики `run_experiment.py`, `compare_runs.py`, `tests/test_compare_runs.py`; подсказывал команды PowerShell.
- Какие фрагменты проверены самостоятельно и какими командами: я скопировал файлы в проект и запустил `ruff check .` (чисто) и `pytest -q` (90 passed); сам выполнил `python -m housing_price.run_experiment --seeds 42 7 13 21 99 --models median_baseline linear_regression random_forest` и `python -m housing_price.compare_runs --experiment housing-price`; значения при seed 42 (88227.5, 49775.6, 33411.2) совпали с контрольными числами тимлида; сам выполнил повторный запуск `train --mlflow`, `mlflow.search_runs` и загрузку модели; проверил `git status` и `git diff` перед коммитами и сам оставил review в PR #35.
