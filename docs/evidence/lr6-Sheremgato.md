# Индивидуальная карточка сдачи ЛР6 — Шереметов Мурат

- **Студент, группа, команда, GitHub:** Шереметов Мурат Олегович, Т26УПМО-Т.МО41, команда №4, @Sheremgato.
- **Commit командной версии:** база `ece964446a4dd88c76ca78ede354b3c88cef1eed` из `upstream/mourberg`; код smoke test и проверенный образ — `357feb8353319cd2d2f445029a0c60bc930fb012`. Итоговый командный tag `lr6-v1` назначает лид.
- **Образ:** `mlops-housing-price:lr6-357feb8`; image ID `sha256:09e0e23bd6f4b57e3f10b7ca05e7a12463862edd026d1c2c0821dc145e911623`, Linux ARM64.
- **Роль:** Smoke-test engineer. В ЛР5 проверял предусловия вычисления метрик; в ЛР6 проверяю готовность HTTP API и контракт прогноза запущенного контейнера.
- **Issue и критерий приемки:** [#54](https://github.com/haiksarg/T26_MLOps/issues/54). Ограниченное ожидание `/readyz`, HTTP 200, типизированный запрос с девятью признаками; конечный положительный `predicted_value`, непустые `model_version` и `request_id`; ненулевой код при ошибке.
- **Личный артефакт:** [скрипт](../../scripts/container_smoke.py), [45 тестовых случаев без Docker](../../tests/container/test_smoke_script.py), [отчет, полученный командой](../../reports/container/lr6-smoke.json), шаг smoke в job `container` и раздел в `docs/container.md`. Работа и карточка находятся в одной ветке `feat/issue-54-container-smoke` для одного PR в `haiksarg:mourberg`; публикация PR пока не выполнена.
- **Команда индивидуальной проверки:** `python3 -I -S scripts/container_smoke.py --base-url http://127.0.0.1:8080 --output reports/container/lr6-smoke.json`. Флаги `-I -S` подтверждают запуск без пакетов из окружения. Сборка выполнена из чистой копии указанного commit с полным набором данных, без локальных окружений и кэшей.
- **Результат проверки:** контейнер `healthy`, inspect — `OK`. Прогноз `446816.70966752135`, версия `random_forest-seed42-data8a3727f4`, `request_id` `8d2a29b3-5dc9-4f88-8d5d-27d529bdb4a5`. Отчет не редактировался вручную. Полный pytest: **274 passed** на macOS и в Docker; Ruff — без замечаний. Одно предупреждение MLflow/SQLAlchemy уже было в исходных 229 тестах.
- **Runtime-ограничение и риск:** процесс работает от `10001:10001`, порт хоста привязан к `127.0.0.1`, healthcheck обращается к `/readyz`. Проверка отличает запущенный процесс от готовой модели и выявляет несовпадение порта процесса с healthcheck и mapping.
- **Defect injection:** во временной копии Dockerfile только порт в последнем `CMD` изменен с `8080` на `8000`; healthcheck и mapping остались на 8080. Ожидался `unhealthy` и timeout smoke test. Фактически Compose вернул `1`, smoke test — `1` за `5.24` с. Файл `defect.json` не создан. Dockerfile восстановлен побайтно; исправный образ снова стал `healthy`, повторный smoke test вернул 0. Дефект не входит в коммиты, временные контейнеры остановлены.
- **Первый полезный фрагмент container log:** приведен ниже; он показывает, почему проверка 8080 не достигла приложения.
- **Инженерное решение и альтернатива:** общий срок ожидания контролируется `time.monotonic`, запросы имеют ограниченное ожидание, опрос идет с короткими паузами. Рассмотренная фиксированная пауза перед запросом не учитывает фактическую готовность API. Коды выхода позволяют использовать тот же скрипт в CI.
- **Результат обучения:** различаю доступность процесса, готовность модели и корректность ответа `/predict`; могу объяснить связь image tag, image ID и commit, а также причину отказа при несовпадении портов.
- **Использование ИИ и проверка:** ИИ-помощник: скрипт и тесты; проверка — pytest, Ruff, Docker.
- **Review:** PR Кирилла @NGHtCONTROLA по ЛР6 пока не опубликован; [#52](https://github.com/haiksarg/T26_MLOps/issues/52) — issue. Проверка его PR и опубликованное review еще не выполнены; ссылку добавлю после публикации. Мой PR проверяет @icy07.

```text
app-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
container t26-lr6-sheremgato-app-1 is unhealthy
Smoke test: timeout: /readyz не готов за 5 с; GET http://127.0.0.1:8080/readyz: запрос или JSON-ответ некорректен
```

Команда отказа: `python3 -I -S scripts/container_smoke.py --timeout 5 --output reports/container/defect.json`.

`dvc.lock`, данные, модели и временная правка Dockerfile в личный diff не входят.
