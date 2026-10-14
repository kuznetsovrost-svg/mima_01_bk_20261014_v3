---
name: fst-project-health-from-md-snapshot
version: 1.0.19
description: "Use when the user wants to retrieve MD snapshots of a project from its MCP card (DocumentId=70139) and build HTML strictly from that snapshot (no live MCP). Modes: --last/--first/--nearest (default, requires --at)/--exact/--pick/--list. --codes X Y Z for trend runs. Never-fail + обязательное логирование в logs/<ISO-timestamp>.log. Заменяет deprecated fst-project-health-from-json."
tags: [snapshot, mcp, pmpractice, ru, foresight, project-health, md, historical, html, read-from-mcp, trend-analysis, never-fail]
related_skills: [fst-project-health, fst-project-health-snap-md, fst-mcp-tester]
---

# fst-project-health-from-md-snapshot

## When to load

- Пользователь говорит: «построй HTML за прошлую дату», «дай отчёт
  по состоянию на 23 сентября», «восстанови MD из карточки», «собери
  трендовый отчёт за неделю», «у меня нет live MCP, есть только
  архив в карточке».
- Пользователь хочет **исторический** отчёт — не текущее состояние
  проекта, а его снимок на конкретный момент.
- Другой скилл/скрипт хочет **только извлечь MD** (без HTML) для
  массовой обработки (трендовый анализ).

## Главные особенности (v1.0.19)

1. **Только MD-снимок** — никаких обращений к live MCP.
2. **5 режимов выбора снимка**: `--last`, `--first`, `--nearest` (default),
   `--exact`, `--pick`.
3. **Массовые прогоны**: `--codes X Y Z` — для трендового анализа.
4. **Never-fail**: каждый проект в `try/except/continue`. Один упавший
   проект не роняет весь прогон.
5. **Обязательное логирование**: каждый запуск = отдельный файл
   в `logs/<ISO-timestamp>.log` с header/body/trailer.

## Что внутри

- `scripts/fetch_snapshot.py` — только извлечение MD из MCP.
- `scripts/build_html.py` — только сборка HTML из MD.
- `scripts/run.py` — обёртка fetch + html (удобно для cron).
- `scripts/logging_utils.py` — утилиты логирования.
- `references/` — playbook, API-описание.
- `logs/` — каталог логов (один файл на запуск).
