# Регресс производительности v1.1.2 (2026-09-03)

Замеры скорости по фазам построения отчёта. **Cold cache** (явно вытерт и перепрогнан с `--no-cache`).

## Когда использовать

- Проверить эффект любого изменения в `project_indicators.py` / `run_all.py` / MCP-фильтрах
- Поймать регресс после обновления `mcp_config.py`, `lc_stage_kt_registry.py`, `point_states.py`
- Замерить эффект prefetch-паттерна (cold vs warm)

## Процедура (повторяемая)

```bash
# 1. Вытереть кэш
rm -fv /tmp/.cache_run_all_*.json /tmp/.cache_project_card_*.json

# 2. На всякий — pycache (не обязательно, но помогает от устаревших .pyc)
find <SKILL_DIR>/scripts -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 3. Каждый проект — ОТДЕЛЬНЫМ запуском с --no-cache --timing
cd <SKILL_DIR>/scripts
python3 run_all.py --code 504-595 --no-cache --timing 2>&1 | tail -25
python3 run_all.py --code 503-152 --no-cache --timing 2>&1 | tail -25
python3 run_all.py --code 503-434 --no-cache --timing 2>&1 | tail -25
python3 run_all.py --code 504-314 --no-cache --timing 2>&1 | tail -25
```

**Почему по одному**: ты хочешь сравнить cold-cache поведение без накопления прогрева MCP-сервера между прогонами.

## Эталон v1.1.2 (cold cache, секции 3–8)

| Фаза | 504-595 | 503-152 | 503-434 | 504-314 |
|---|---:|---:|---:|---:|
| find_project | 3.16 | 3.29 | 3.18 | 3.11 |
| save_project_json | 2.33 | 2.35 | 2.35 | 2.13 |
| load_project_points | 0.79 | 0.96 | 0.83 | 0.77 |
| load_project_entity | 2.36 | 2.22 | 2.28 | 2.12 |
| section_3 | 0.00 | 0.00 | 0.00 | 0.00 |
| **section_4** | **5.51** | **22.41 ⚠️** | 8.37 | 7.81 |
| section_5 | 0.00 | 0.00 | 0.00 | 0.00 |
| **section_6_indicators** | **18.35** | **34.87 ⚠️** | **18.78** | **17.37** |
| section_6 | 1.38 | 1.44 | 1.36 | 1.28 |
| section_7 | 3.16 | 3.14 | 3.37 | 3.16 |
| section_8 | 0.00 | 0.00 | 0.00 | 0.00 |
| rebuild_md | 0.04 | 0.04 | 0.03 | 0.04 |
| build_html | 0.01 | 0.01 | 0.00 | 0.00 |
| build_word | 0.18 | 0.61 | 0.22 | 0.21 |
| **TOTAL** | **37.27** | **71.33** | **40.79** | **38.00** |

Снято 2026-09-03, ROSTISLAV.

## Наблюдения

### Узкое место №1: `section_6_indicators` (17–35 сек, 45–50% TOTAL)

- Подтверждено в 4/4 прогонов.
- Подозрение: 6.10 + 6.13 (оба читают `ProjectBudgetCompleteBusiness`). См. `references/indicator-6-10-direct-costs.md` и `references/indicator-6-13-budget.md`.
- На warm-cache (со2-го прогона, prefetch v1.0.1) это падает до ~8 сек (эффект -74%, см. memory: 32.93→8.43 сек).

### Аномалия 503-152 (нужно расследовать!)

- `section_4`: **22.41 сек** vs норма 5–8 сек у других проектов (в 3–4× медленнее).
- `section_6_indicators`: **34.87 сек** vs норма 17–19 сек (в ~2× медленнее).
- TOTAL: **71.33 сек** vs 37–41 у остальных (почти 2×).

**Гипотезы (требуют проверки):**
1. У 503-152 больше точек КТ / бюджетных строк — `load_project_points` 0.96 сек (чуть выше) это косвенно подтверждает.
2. Попадает в тяжёлую ветку 6.10/6.13 — например, фильтры `startdate`/`enddate` не сработали и сервер вернул ВСЕ бюджеты, а не диапазон.
3. `section_4` использует `get_entity_data` для Project — возможно, у 503-202 аномально большой JSON свойств.

**TODO**: расследовать — открыть `references/indicator-6-13-budget.md` и `references/indicator-6-10-direct-costs.md`, проверить что у 503-152 в `startdate`/`enddate`.

## Связанные ссылки

- `references/optimization-v1-1-2.md` — узкое место 6.10 + 6.13 = 50% (предыдущая эталонная таблица)
- `references/run-all-procedure.md` — базовая процедура запуска
- `references/v1-0-0-session-learnings.md` — узкие места и уроки v1.0.0
- Pitfall #152 (SKILL.md) — проверять через `list_view` перед добавлением фильтров
- Pitfall #159 (SKILL.md) — `project_id=accountid` (фикс в 6.7)
- Pitfall #165 (SKILL.md) — 3 интеграционных бага при добавлении секции 6
- Pitfall #181 (SKILL.md) — verdict label «Критическое замечание»
