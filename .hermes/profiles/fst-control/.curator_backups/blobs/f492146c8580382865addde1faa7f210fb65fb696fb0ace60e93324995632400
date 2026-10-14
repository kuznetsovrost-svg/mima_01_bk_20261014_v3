# MCP-server regression — 2026-08-31

**Дата:** 2026-08-31
**Критичность:** высокая — ломает `build_section_6`

---

## Что сломалось

`Project/ProjectHealthCostMy?ProjectId=<id>` снова возвращает **0 строк**.

### История (по дням)

| Дата | `ProjectHealthCostMy?ProjectId=4595` | Замечание |
|------|--------------------------------------|-----------|
| 2026-08-21 | работает (1 строка) | исходное состояние |
| 2026-08-23 | ❌ 500 (bigint = text) | регрессия 1 |
| 2026-08-26 | ✅ работает (1 строка) | починили (письмо v3) |
| 2026-08-31 | **0 строк** (200 OK, но пусто) | **регрессия 2** |

### Текущее поведение (2026-08-31)

```python
view = "ProjectHealthCostMy?ProjectId=4595"
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": view,
    "limit": 10
})
# r["data"] == []  ← пустой массив, не ошибка
```

### Эффект на скилл

`build_section_6()` в `scripts/run_all.py`:

```python
project_row = rows[0] if rows else None
if not project_row:
    result = {"section_health": "Неопределено", ...}
```

→ Раздел 6 (Финансы) в отчёте = **«Неопределено»** со всеми показателями «Нет / Нет данных», хотя сами данные **доступны** через `ProjectBudgetCompleteBusiness` (12 строк для 504-595).

---

## Workaround: рассчитывать показатели самостоятельно

### Источники данных (по убыванию надёжности)

| View | Работает? | Что даёт |
|------|:---------:|----------|
| `ProjectBudgetCompleteBusiness?ProjectId=<id>` | ✅ стабильно | 12+ строк (акты + оплаты) с actplansum/actfactsum/payplansum/payfactsum |
| `ProjectHealthCostMy?ProjectId=<id>` | ❌ регрессия (0 строк) | агрегаты (plan/forecast/deviation/devcost) |

### Формулы расчёта из `ProjectBudgetCompleteBusiness`

| Показатель | Из PBCB | Из PHCM | Формула |
|------------|--------|---------|---------|
| **Σ актов (план)** | ✅ | — | Σ `actplansum` where `isincome=True` |
| **Σ актов (факт)** | ✅ | — | Σ `actfactsum` |
| **Σ актов (прогноз)** | ✅ | — | Σ `actforecastsum` |
| **Σ оплат (план)** | ✅ | — | Σ `payplansum` where `ispayment=True` |
| **Σ оплат (факт)** | ✅ | — | Σ `payfactsum` |
| **Σ оплат (прогноз)** | ✅ | — | Σ `payforecastsum` |
| `forecast` (фин.рез-т) | рассчитать | direct | `Σ actforecastsum - Σ payforecastsum` |
| `plan` (фин.рез-т) | рассчитать | direct | `Σ actplansum - Σ payplansum` |
| `devcost` | ⚠️ нет | direct | `?` — не документировано (pitfall #12.3) |
| `devallcost` | ⚠️ нет | direct | `?` — не документировано |

### Пример для 504-595 (ProjectId=4595)

Live-probe 2026-08-31:

```
=== АКТЫ (доходы) — 7 строк из PBCB?ProjectId=4595 ===
  План:    6 497 500.00 ₽
  Прогноз: 6 497 490.00 ₽
  Факт:    2 500 000.00 ₽

=== ОПЛАТЫ (расходы) — 5 строк (isincome=False или 0 в фильтре) ===
  Все суммы = 0 ₽

=== Расчётные показатели ===
  Δ актов (факт-план):    −3 997 500 ₽
  Маржа (факт):           2 500 000 ₽
  Прогноз фин.рез-та:    6 497 490 ₽  (> 0, убытка нет)
```

Сравнение со СТАРЫМИ данными (PHCM работала, 2026-08-21):

| Поле | Из PHCM (2026-08-21) | Из PBCB+расчёт (2026-08-31) |
|------|---------------------|----------------------------|
| `forecast` | −221 860 ₽ (убыток) | **6 497 490 ₽** (прибыль) |
| `devcost` | 4 146 860 ₽ | — (не рассчитывается) |

**Расхождение объясняется** тем, что данные в `ProjectHealthCostMy` (агрегат на весь проект) и в `ProjectBudgetCompleteBusiness` (только через InContract) считают **разные наборы операций**. Для 504-595 — большая часть операций, видимо, не через контракт.

---

## Что нужно сделать в скилле

### 1. Fallback-логика в `build_section_6()`

```python
# Текущая логика:
view_name = PROJECT_HEALTH_COST_MY_VIEW_FOR(project["project_id"])
resp = mcp_call(sid, "get_view", {"entityName": "Project", "viewName": view_name, "limit": 100})
rows = resp.get("data", [])
project_row = rows[0] if rows else None

# Нужно добавить fallback на ProjectBudgetCompleteBusiness:
if not project_row:
    pb_view = PROJECT_BUDGET_VIEW_FOR(project["project_id"])
    pb_resp = mcp_call(sid, "get_view", {"entityName": "Project", "viewName": pb_view, "limit": 1000})
    pb_rows = pb_resp.get("data", [])
    if pb_rows:
        # Рассчитать агрегаты самостоятельно
        acts = [r for r in pb_rows if r.get("isincome")]
        pays = [r for r in pb_rows if r.get("ispayment")]
        project_row = {
            "forecast": sum((r.get("actforecastsum") or 0) for r in acts) - sum((r.get("payforecastsum") or 0) for r in pays),
            "plan": sum((r.get("actplansum") or 0) for r in acts) - sum((r.get("payplansum") or 0) for r in pays),
            "fact": sum((r.get("actfactsum") or 0) for r in acts) - sum((r.get("payfactsum") or 0) for r in pays),
            "inplan": sum((r.get("actplansum") or 0) for r in acts),
            "infact": sum((r.get("actfactsum") or 0) for r in acts),
            "outplan": sum((r.get("payplansum") or 0) for r in pays),
            "outfact": sum((r.get("payfactsum") or 0) for r in pays),
            "outallforecast": sum((r.get("payforecastsum") or 0) for r in pays),
            "deviation": (sum((r.get("actforecastsum") or 0) for r in acts) - sum((r.get("payforecastsum") or 0) for r in pays)) - (sum((r.get("actplansum") or 0) for r in acts) - sum((r.get("payplansum") or 0) for r in pays)),
            # devcost / devallcost не рассчитываются — оставить 0
            "devcost": 0,
            "devallcost": 0,
        }
```

### 2. ⚠️ ВНИМАНИЕ: данные НЕ идентичны

`ProjectHealthCostMy` (агрегат) ≠ `ProjectBudgetCompleteBusiness` (только через InContract).

Разные семантики:
- **PHCM** — весь проект (включая операции без контракта).
- **PBCB** — только операции через InContract.

Если использовать PBCB как fallback — **показатели могут отличаться** от исторических (когда PHCM работала). Нужно явно отметить в отчёте: «источник: ProjectBudgetCompleteBusiness (fallback)».

### 3. Условие fallback в `compute_verdict()`

Если `devcost == 0` (потому что не рассчитан из PBCB) → **нельзя оценивать показатель 2** (Δ текущей стоимости). Считать его «Неопределено»:

```python
p2_ok = abs(devcost) > thr_devcost  # будет False при devcost=0
p2 = {"result": "Неопределено" if devcost == 0 else ("Да" if p2_ok else "Нет"), ...}
```

---

## Чек-лист после исправления

```bash
# 1. Проверить что fallback работает:
python3 -c "
import sys
sys.path.insert(0, '/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts')
from mcp_config import mcp_init, mcp_call, PROJECT_BUDGET_VIEW_FOR, PROJECT_HEALTH_COST_MY_VIEW_FOR
sid, _ = mcp_init(client_name='fallback-test')
phcm = mcp_call(sid, 'get_view', {'entityName': 'Project', 'viewName': PROJECT_HEALTH_COST_MY_VIEW_FOR(4595), 'limit': 10})
pbcb = mcp_call(sid, 'get_view', {'entityName': 'Project', 'viewName': PROJECT_BUDGET_VIEW_FOR(4595), 'limit': 1000})
print(f'PHCM rows: {len(phcm.get(\"data\", []))}')  # 0
print(f'PBCB rows: {len(pbcb.get(\"data\", []))}')  # 12
"

# 2. Pipeline должен работать без ошибок:
rm -f /tmp/.cache_run_all_504-595.json
python3 scripts/run_all.py --code 504-595 --no-word --timing
# → section_6 = "Болен" (не "Неопределено") благодаря fallback

# 3. Тесты остаются 6/6:
cd tests && python3 run_all_tests.py
```

---

## Связанные документы

- `references/mcp-server-filter-playbook.md` — статусы view (PHCM был ✅, теперь ❌)
- `references/mcp-regression-2026-08-27.md` — предыдущая регрессия (InContractMyProject)
- `references/forsight-mcp-quirks.md` раздел 12.3 — семантика `fact`/`forecast` неясна
- `references/run-all-pitfalls-2026-08-22.md` — Bug #73 (MetaModel ключи) — аналогичный класс багов

---

## Контакт

- **Telegram:** @kuznetsov-rostislav (или через Hermes-агент)
- **Дата:** 2026-08-31
- **Скилл:** `fst-project-health` v0.13.0