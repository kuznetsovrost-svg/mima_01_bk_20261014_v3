# Trend Reports via Date Filters — `ProjectHealthCostMy` с `DateBegin/DateEnd`

**Дата:** 2026-09-01
**Live-probe:** 504-595 (ProjectId=4595) — 11 точек за 10 месяцев

---

## Главное открытие

`ProjectHealthCostMy` поддерживает **фильтр по отчётному периоду** — `DateBegin` / `DateEnd`. Это позволяет получать **исторические данные** проекта на разные даты.

## Формат вызова

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",
    "filters": {
        "ProjectId": 4595,
        "DateBegin": "2026-08-01",
        "DateEnd": "2026-08-31"
    },
    "limit": 100
})
# → 1 строка с историческими данными на конец августа
```

## Поддерживаемые фильтры

Из `list_views` (live-probe 2026-09-01):

| View | Filters |
|------|---------|
| **ProjectHealthCostMy** | **ProjectId, DateBegin, DateEnd**, ProjectProfileId |
| ProjectResourcePlan | ProjectId |
| ProjectBudgetCompleteBusiness | ProjectId, ContractId, ProgramId, PortfolioId |
| InContractMyProject | ProjectId |
| AllMyPoint | PortfolioId, ProjectId |
| **NormDayWorkHours** | **ProjectId, StartDate, EndDate** |

## Реальные данные 504-595 (live-probe 2026-09-01)

| Период | Forecast | Fact | Devcost | Inplan | Infact |
|--------|---------:|-----:|--------:|-------:|-------:|
| 2025-11 | −221 860 | 0 | 0 | 0 | 0 |
| 2025-12 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-01 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-02 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-03 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-04 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-05 | −221 860 | 0 | 0 | 0 | 0 |
| **2026-06** | −221 860 | **−753 525** | 719 202 | 0 | 0 |
| **2026-07** | −221 860 | **9 110** | **2 173 874** | **4 997 500** | **2 500 000** |
| **2026-08** | −221 860 | 0 | **1 253 784** | 1 500 000 | 0 |

**Активность появляется с июня 2026.** До этого — нули.

## Trend Report — рабочий пример

Скрипт `/tmp/trend-report-design/scripts/build_trend_report.py`:

```bash
python3 /tmp/trend-report-design/scripts/build_trend_report.py \
  --code 504-595 \
  --period 300 \
  --output /tmp/project_504-595_trend_report.html
```

**Что делает:**
1. Подключается к MCP
2. Получает список views через `list_views` (для проверки доступных фильтров)
3. Генерирует список периодов (последние N месяцев)
4. Для каждого периода запрашивает `ProjectHealthCostMy` с `DateBegin/DateEnd`
5. Собирает данные
6. Генерирует SVG-графики (5 метрик: forecast, fact, devcost, inplan, infact)
7. Сохраняет HTML и JSON

**Результат:** HTML 18 КБ, 5 SVG-графиков, 11 точек данных.

## Готовый файл

`/tmp/project_504-595_trend_report.html` — пример с 5 графиками:
- Прогноз фин.результата
- Текущий финансовый результат
- Δ текущей стоимости от плана
- Плановый доход
- Фактический доход

## Будущее применение — скилл `fst-project-trends`

Это основа для будущего скилла `fst-project-trends`:
- Получает JSON-отчёты за разные даты из MCP
- Строит трендовые графики (Inline SVG, без зависимостей)
- Показывает динамику по 5 метрикам

**Не применять к текущему скиллу** — пользователь сказал «спроектируем → потом создадим». Дизайн в `/tmp/trend-report-design/`.

## Что работает, что нет

| Что | Статус |
|-----|:------:|
| `DateBegin/DateEnd` фильтр | ✅ работает |
| `ProjectId` фильтр | ✅ работает |
| Получение данных за разные месяцы | ✅ работает |
| **Изменение данных между месяцами** | **✅ работает!** |
| `ProjectHealthCostMy` без фильтра | ❌ 500 `параметр $5` |

## Pitfalls

1. **`DateBegin/DateEnd` включают оба конца.** То есть `DateBegin=2026-08-01&DateEnd=2026-08-31` — это август целиком.
2. **1 строка на проект на период** — это **агрегат**, не список строк. Не пытаться получить "историю изменений" — это всегда текущий snapshot на конец периода.
3. **Forecast стабилен** (`-221 860` для 504-595) — прогноз не меняется задним числом.
4. **Fact/Devcost/Inplan/Infact меняются** — это динамические показатели.

## Скрипт для воспроизведения

```python
import sys
import importlib.util
sys.path.insert(0, '/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts')
spec = importlib.util.spec_from_file_location('mcp_config', '/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/mcp_config.py')
mcp_config = importlib.util.module_from_spec(spec)
sys.modules['mcp_config'] = mcp_config
spec.loader.exec_module(mcp_config)

sid, _ = mcp_config.mcp_init(client_name='trend-probe')

# Получить данные за 10 месяцев
for year, month in [(2025, m) for m in range(11, 13)] + [(2026, m) for m in range(1, 10)]:
    r = mcp_config.mcp_call(sid, 'get_view', {
        'entityName': 'Project',
        'viewName': 'ProjectHealthCostMy',
        'filters': {
            'ProjectId': 4595,
            'DateBegin': f'{year}-{month:02d}-01',
            'DateEnd': f'{year}-{month:02d}-{28 if month==2 else 30 if month in [4,6,9,11] else 31}'
        },
        'limit': 100
    })
    rows = r.get('data', [])
    if rows:
        d = rows[0]
        print(f"{year}-{month:02d}: forecast={d.get('forecast') or 0:>10,.0f}, fact={d.get('fact') or 0:>10,.0f}")
```