# Роли команды №4 в ЛР1

Тема проекта: прогнозирование стоимости жилья (Housing Price Prediction).
В команде три участника, поэтому пять ролей ЛР1 совмещаются. У каждого участника
своя issue и свой проверяемый артефакт в общей версии `lr1-v1`.

| Участник | GitHub | Роль в ЛР1 | Зона результата | Issue | Ветка для PR |
|---|---|---|---|---|---|
| Саргсян Айк | [@haiksarg](https://github.com/haiksarg) | Release lead, Repository administrator | План ЛР1 и issues, связи issue–PR, правила `main`, шаблоны issue и PR, tag `lr1-v1` | [#1](https://github.com/haiksarg/T26_MLOps/issues/1) | `chore/issue-1-repo-governance` |
| Ильин Андрей | [@icy07](https://github.com/icy07) | Environment engineer, Quality engineer | Версия Python, проверенные команды установки и запуска в README, чистая установка, CI (Ruff, pytest) | [#2](https://github.com/haiksarg/T26_MLOps/issues/2) | `adreyil` |
| Шереметов Мурат | [@Sheremgato](https://github.com/Sheremgato) | Documentation and risk reviewer | ADR 0001, CONTRIBUTING, CODEOWNERS, проверка рисков | [#3](https://github.com/haiksarg/T26_MLOps/issues/3) | `mourberg` |

## Как изменения попадают в `main`

1. Участник работает в своем форке репозитория `haiksarg/T26_MLOps` в ветке с понятным именем.
2. Pull request из форка в свою ветку (`adreyil` или `mourberg`) — review Release lead.
3. Pull request из своей ветки в `main` с `Closes #N` — review и merge Release lead.
4. Изменения Release lead проходят через pull request в `main` с review другого участника.

Правила `main` и исключения процесса: [docs/evidence/lr1-branch-rules.md](evidence/lr1-branch-rules.md).

# Роли команды №4 в ЛР2

Пять ролей ЛР2 совмещаются. Работа собирается в ветке `lab2/data-contract`
и попадает в `main` одним pull request.

| Участник | Роль в ЛР2 | Зона результата | Issue |
|---|---|---|---|
| Саргсян Айк ([@haiksarg](https://github.com/haiksarg)) | Contract engineer, Repository and documentation reviewer | Образец и его происхождение, `data/contract.json`, политика Git для данных, README, итоговый PR, tag `lr2-v1` | [#13](https://github.com/haiksarg/T26_MLOps/issues/13) |
| Ильин Андрей ([@icy07](https://github.com/icy07)) | Quality engineer | Валидатор, отрицательные тесты, проверка данных в CI | [#14](https://github.com/haiksarg/T26_MLOps/issues/14) |
| Шереметов Мурат ([@Sheremgato](https://github.com/Sheremgato)) | Data steward, Leakage reviewer | Карточка данных, стратегия разделения, `FEATURES` и тест против утечки | [#15](https://github.com/haiksarg/T26_MLOps/issues/15) |

Путь изменений участников: форк → своя ветка (`adreyil`, `mourberg`) — review Release lead →
`lab2/data-contract` → итоговый PR в `main` с review участника, который не является автором.
