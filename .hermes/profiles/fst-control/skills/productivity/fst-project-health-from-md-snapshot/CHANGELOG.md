# Changelog — fst-project-health-from-md-snapshot

## v1.0.19 — 2026-09-24

**Первая версия.** Заменяет deprecated `fst-project-health-from-json`.

### Что появилось

- `scripts/fetch_snapshot.py` — извлечение MD-снимков из карточек проектов
  в MCP через `list_files` + `resources/read`.
- 5 режимов выбора снимка: `--last`, `--first`, `--nearest` (default),
  `--exact`, `--pick`. Плюс `--list` для простого просмотра.
- `--codes X Y Z` — массовый прогон (для трендового анализа).
- `scripts/build_html.py` — обёртка над `fst-project-health/scripts/build_html_report.py --md`.
- `scripts/run.py` — удобная обёртка «fetch + html» для cron'а.
- `scripts/logging_utils.py` — утилиты логирования, идентичные
  `fst-project-health-snap-md`.
- `logs/<ISO-timestamp>.log` — отдельный лог на каждый запуск.
  Header (дата, аккаунт, роль, action, args, проекты) → body (на каждый
  проект ✓/✗ + type/message) → trailer в `finally:`.
- Never-fail: каждый проект в `try/except/continue`. Один упавший не
  роняет весь прогон.
- `references/api.md` — для программного использования из Python.
- `playbook.md` — с секцией «Принципы логирования и устойчивости»
  и «Режимы массового вызова».

### Кэш

`~/.hermes/profiles/fst-control/cache/snapshots/<code>_<timestamp>.md`.
Не ротируется автоматически.

### Зависимости

- PMForesight MCP (`MCP_URL=https://ppreplica.hera.pmpractice.ru/mcp`).
- `fst-project-health` — для переиспользования `build_html_report.py --md`.
- `requests` (pip).

### Не делал

- **Ротация кэша** — ответственность pipeline'а.
- **DOCX из MD** — это `fst-project-health-word` (отдельный скилл).
- **Сравнение снимков** — для трендов. Можно сделать скриптом поверх
  `fetch_snapshot`, см. `references/api.md`.
