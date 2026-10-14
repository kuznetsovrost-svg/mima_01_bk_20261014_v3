# Task: <краткое имя задачи>
state: draft                       # draft | in_progress | blocked | review | done
profile: mi_mg_01
created: YYYY-MM-DD
updated: YYYY-MM-DD
author: Rost
priority: normal                  # low | normal | high | urgent

## Goal
Что нужно сделать в 1-2 строки. Конкретно и измеримо.

## Context (опционально)
Зачем эта задача. Где используется результат. Какие ограничения.

## Requirements
- <требование 1 — измеримое>
- <требование 2>
- <требование 3>

## Inputs
Файлы, которые будут переданы агенту (уже скопированы в inputs/):
- inputs/<file1.ext> — описание
- inputs/<file2.ext> — описание

## Outputs
Что должно получиться на выходе:
- results/<task-id>/<output1.ext> — описание
- results/<task-id>/<output2.md> — описание

## Acceptance Criteria (чеклист)
- [ ] критерий 1
- [ ] критерий 2
- [ ] критерий 3

## Constraints / Limits
- Бюджет токенов: <например, <5000>
- Время выполнения: <например, <30 мин>
- Sensitive data: <нет / есть — какая>

## Style Guide (опционально)
Ссылки на:
- references/style-guide.md (общий)
- inputs/<task-id>/refs/<конкретное>

## Status Log (обновлять по ходу)
- YYYY-MM-DD HH:MM — created
- <обновления по мере работы>

## Decisions (опционально)
Почему был выбран тот или иной подход. Полезно для аудита.
