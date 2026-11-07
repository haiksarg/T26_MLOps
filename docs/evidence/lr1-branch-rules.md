# Правила веток репозитория (ЛР1)

Правила настроены через GitHub Rulesets: **Settings → Rules → Rulesets**.
Проверить действующие правила для `main`:

```bash
gh api repos/haiksarg/T26_MLOps/rules/branches/main
```

## Соответствие требованиям ЛР1 (п. 7.5)

| Требование ЛР1 | Настройка | Статус |
|---|---|---|
| Merge только через pull request | `pull_request` в ruleset `main-protection` | Включено |
| Минимум одно одобрение другого участника | `required_approving_review_count: 1`; автор не может одобрить свой PR | Включено, см. исключение ниже |
| Одобрение относится к актуальному diff | `dismiss_stale_reviews_on_push: true` — новый commit сбрасывает одобрение | Включено |
| Обязательное разрешение обсуждений | `required_review_thread_resolution: true` | Включено |
| Обязательная успешная проверка `quality` | `required_status_checks`: job `quality` из `.github/workflows/ci.yml` | Включено |
| Запрет force push и удаления ветки | `non_fast_forward`, `deletion` | Включено |
| Одобрение последнего push участником, который его не отправлял | `require_last_push_approval: false` | Не включено, см. исключение ниже |

Дополнительно:

- Способ слияния — только merge commit (`allowed_merge_methods: ["merge"]`, squash и rebase
  отключены в настройках репозитория). Коммиты участников сохраняют SHA на пути
  «форк → ветка участника → `main`», поэтому ссылки в evidence card и `git log` совпадают.
- Ветки участников `adreyil` и `mourberg` защищены ruleset `member-branches` от удаления и force push.

## Исключения и эквивалентный процесс

1. **Участники работают в форках и не являются коллабораторами репозитория.** GitHub засчитывает
   в правило одобрения только review пользователей с правом записи. Поэтому администратор
   (`@haiksarg`) включен в список обхода с режимом `pull_request`: он может слить свой PR
   без засчитанного одобрения, но **не может** делать прямой push в `main`.
   Процесс: собственный PR администратора сливается только после review другого участника
   (оставленного в PR, даже если GitHub его не засчитывает) и успешного job `quality`.
2. **Одобрение последнего push.** Изменения участников попадают в `main` в два шага: PR из форка
   в ветку участника и PR из ветки участника в `main`. Последний push в ветку участника —
   merge commit, который создает Release lead при принятии первого PR. Если включить правило,
   Release lead не сможет одобрить второй PR, а других участников с правом записи нет.
   Процесс: Release lead проверяет оба PR; содержимое второго PR совпадает с уже проверенным первым.

## Журнал изменений правил

- 2026-10-07 — rulesets созданы.
- 2026-10-07 — до первого pull request участников rulesets на несколько минут переводились в `disabled`,
  чтобы переоформить сообщения первых коммитов (`git commit --amend` и force push; содержимое файлов
  не менялось). Затем rulesets включены с прежней конфигурацией — она совпадает с экспортом ниже.
- 2026-11-07 — в ruleset `member-branches` добавлена ветка `komlev` нового участника @NGHtCONTROLLA.

## Экспорт правил

Получено командой `gh api repos/haiksarg/T26_MLOps/rulesets/<id>`.

### `main-protection` (id 24669344)

```json
{
  "bypass_actors": [
    {
      "actor_id": 5,
      "actor_type": "RepositoryRole",
      "bypass_mode": "pull_request"
    }
  ],
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "~DEFAULT_BRANCH"
      ]
    }
  },
  "enforcement": "active",
  "name": "main-protection",
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "parameters": {
        "allowed_merge_methods": [
          "merge"
        ],
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_extra_approval_for_unattributed_changes": true,
        "require_last_push_approval": false,
        "required_approving_review_count": 1,
        "required_review_thread_resolution": true,
        "required_reviewers": []
      },
      "type": "pull_request"
    },
    {
      "parameters": {
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {
            "context": "quality",
            "integration_id": 15368
          }
        ],
        "strict_required_status_checks_policy": false
      },
      "type": "required_status_checks"
    }
  ],
  "target": "branch"
}
```

### `member-branches` (id 24669346)

```json
{
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "refs/heads/adreyil",
        "refs/heads/mourberg"
      ]
    }
  },
  "enforcement": "active",
  "name": "member-branches",
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    }
  ],
  "target": "branch"
}
```
