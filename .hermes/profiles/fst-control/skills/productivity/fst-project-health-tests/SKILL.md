---
name: fst-project-health-tests
version: 1.0.19
description: "Use when the user asks to run tests, check that sкиллы still work after changes, or wants regression checks for the fst-project-health-* family. Запускает группы тестов: regression, MCP write/read, snap-md (генератор), from-md-snapshot (извлекатель), cross-skill интеграция, 4 инварианта устойчивости. По умолчанию MCP-тесты ВКЛЮЧЕНЫ. Каждый тест — never-fail (транспортный flake = SKIP, не FAIL). Лог пишется в logs/tests.log."
tags: [tests, regression, mcp, pmpractice, ru, foresight, project-health, never-fail, validation]
related_skills: [fst-project-health, fst-project-health-snap-md, fst-project-health-from-md-snapshot, fst-mcp-tester]
---

# fst-project-health-tests

## When to load

- «Прогони тесты», «сделай регрессию», «всё ли работает?»
- После больших правок в `fst-project-health*` скиллах.
- В cron для еженедельной проверки (отдельные группы, см. PLAYBOOK).
- Когда хочется убедиться, что MCP write/read работают корректно (после
  обновления стенда / после подозрительного flake).

## Главные особенности (v1.0.19)

1. **6 групп тестов**, каждая запускается отдельно (5–10 минут полный цикл).
2. **MCP-тесты по умолчанию включены** (группа `mcp`).
3. **Never-fail** для тестов: транспортный flake (ReadTimeout,
   ConnectionError) → SKIP с пометкой «MCP transport flake», не FAIL.
4. **Retry 3×** на каждый MCP-вызов с exponential backoff.
5. **Логи в logs/tests.log** — каждый прогон отдельной строкой.
6. **Понятные коды возврата**: 0 (всё ОК), 1 (есть FAIL), 2 (все MCP
   тесты SKIPPED).
