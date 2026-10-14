# Task: sample-stats — анализ events.csv
state: draft
profile: mi_mg_01
created: 2026-07-04
updated: 2026-07-04
author: Rost
priority: normal

## Goal
Посчитать статистику использования по CSV `events.csv`:
- общее число пользователей и событий;
- top-10 по числу событий;
- top-5 по активным действиям (upload/download);
- события по часам (распределение по времени суток);
- уникальные пользователи по дням.

## Context
Демонстрационная задача для проверки скилла `mi_mg_01` и шаблонов
`workspace/`. Это «sample run» без реальной инфраструктуры —
агрегаты по синтетическому логу.

## Requirements
- На входе: `inputs/events.csv` с колонками `user_id,username,event_at,action`.
- Подсчёт по реальному содержимому файла (не выдумывать числа).
- Допускается Python (`python3 -c '...'` или короткий скрипт в `outputs/`).
- Без интерактивных подтверждений — задача полностью автоматическая.

## Inputs
- `inputs/events.csv` — синтетический лог (1000 байт, 26 строк).

## Outputs
- `results/${TASK_ID}/top_users.txt` — top-10 пользователей по числу событий.
- `results/${TASK_ID}/actions_summary.md` — markdown-отчёт со сводкой.
- (опционально) `results/${TASK_ID}/stats.json` — структурированные данные.

## Acceptance Criteria
- [ ] все три файла созданы в `results/${TASK_ID}/`;
- [ ] цифры соответствуют содержимому `events.csv` (можно пересчитать вручную);
- [ ] отчёт читается без контекста (самодостаточный);
- [ ] стиль соответствует `references/style-guide.md`;
- [ ] план в `plans/${TASK_ID}.md` синхронизирован (status обновлён);
- [ ] `progress.json` рядом с этим task-файлом создан и обновлён.

## Constraints
- Бюджет токенов: <3000 на весь task.
- Время выполнения: <2 минуты wall-clock.
- Sensitive data: нет.

## Style Guide
См. `~/.hermes/profiles/mi_mg_01/workspace/references/style-guide.md`.

## Status Log
- 2026-07-04 13:36 — created (Rost)
- 2026-07-04 HH:MM — agent started
- 2026-07-04 HH:MM — outputs ready

## Decisions
- Использовать Python stdlib (csv, collections) — на этом сервере
  pip-окружение можно не трогать.
- Время суток группировать по hour-бакетам 00-23.

## Out of scope
- Сетевые графики по дням (это потребует matplotlib);
- A/B-тесты;
- Перенос в другую СУБД.
