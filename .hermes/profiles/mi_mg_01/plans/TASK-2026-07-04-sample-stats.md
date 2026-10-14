# Plan: TASK-2026-07-04-sample-stats

## State
**draft**

## Profile
mi_mg_01

## Created
2026-07-04 13:36

## Goal
Подсчёт статистики использования по `events.csv`.

## Шаги выполнения
- [ ] 2026-07-04 13:36 — задача создана (Rost)
- [ ] 2026-07-04 — agent стартовал
- [ ] 2026-07-04 — прочитан `inputs/events.csv`
- [ ] 2026-07-04 — подсчитаны:
  - [ ] общее число пользователей
  - [ ] общее число событий
  - [ ] top-10 пользователей по событиям
  - [ ] top-5 по активным действиям (upload/download)
  - [ ] события по часам суток
  - [ ] уникальные пользователи по дням
- [ ] 2026-07-04 — outputs записаны в `results/...`
- [ ] 2026-07-04 — `progress.json` обновлён

## Errors
(пусто)

## Outputs (план)
- results/TASK-2026-07-04-sample-stats/top_users.txt
- results/TASK-2026-07-04-sample-stats/actions_summary.md

## Связанные ссылки
- `workspace/inbox/TASK-2026-07-04-sample-stats/task.md` — промпт.
- `workspace/inbox/TASK-2026-07-04-sample-stats/inputs/events.csv` — данные.
- `workspace/references/style-guide.md` — стиль вывода.
- `workspace/references/templates/report-template.md` — шаблон отчёта.
