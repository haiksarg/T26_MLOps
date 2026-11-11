# Evidence card ЛР5 — @haiksarg

| Поле | Значение |
|---|---|
| Студент | Саргсян Айк Андраникович, группа Т26УПМО-Т.МО41, команда №4, GitHub [@haiksarg](https://github.com/haiksarg) |
| Роль | Integration engineer и Quality reviewer. В ЛР4 — журналирование экспериментов в MLflow; в ЛР5 — структура тестов, bundle, сквозной smoke-тест, отчеты и review |
| Задача | [Issue #39](https://github.com/haiksarg/T26_MLOps/issues/39): слои тестов, `conftest.py`, bundle, smoke-тест, JUnit XML, таблица рисков |
| Личный артефакт | Smoke-тест [`tests/pipeline/test_smoke.py::test_validate_train_load_predict`](https://github.com/haiksarg/T26_MLOps/blob/ebdda7294073a54ca599cdc7b80d92653d5a2c83/tests/pipeline/test_smoke.py#L41) (commit [`ebdda72`](https://github.com/haiksarg/T26_MLOps/commit/ebdda7294073a54ca599cdc7b80d92653d5a2c83)); fixtures `pipeline_frame`, `csv_factory`, `params` и слои тестов (commit [`a8605b9`](https://github.com/haiksarg/T26_MLOps/commit/a8605b9a3f0dec93d59c77bb4c8418577c98688d)); bundle и `load_bundle` (commit [`ca279c0`](https://github.com/haiksarg/T26_MLOps/commit/ca279c057ba82a309a0d14e557f5e39eb82454ea)); review [PR #44](https://github.com/haiksarg/T26_MLOps/pull/44#pullrequestreview-5863649831) и [PR #45](https://github.com/haiksarg/T26_MLOps/pull/45#pullrequestreview-5863792756); итоговый PR [#43](https://github.com/haiksarg/T26_MLOps/pull/43) |
| Контролируемый риск | Модель обучается на данных, которые не прошли контракт: `train` должен вернуть код 2 и не создать файл модели |
| Defect injection | Из `load_validated_data` удалена проверка `report["passed"]`. Заранее названный тест [`tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract`](https://github.com/haiksarg/T26_MLOps/blob/ebdda7294073a54ca599cdc7b80d92653d5a2c83/tests/pipeline/test_smoke.py#L57) упал; дефект удален, тест снова прошел |
| Диагностика | `assert run_train() == 2` → `E assert 0 == 2` (`tests/pipeline/test_smoke.py:63`). Причина: валидатор вернул код 1, но без проверки `passed` обучение завершилось успешно. Фрагмент — в [docs/testing.md](../testing.md#отрицательный-отчет) |
| Воспроизведение | Один тест: `python -m pytest -q tests/pipeline/test_smoke.py::test_train_refuses_data_that_failed_contract`. Весь набор: `python -m pytest -q --junitxml=reports/tests/lr5-pass.xml` |
| Использование ИИ | Claude Code: написал код и тесты моей части, выполнил defect injection, проверил PR участников и подготовил тексты review. Решения по распределению работ и порядку принятия PR — мои |
