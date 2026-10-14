# Playbook: server-side фильтры в имени view

**Дата:** 2026-08-21 (обновлено 2026-08-22)
**Кем:** ROSTISLAV KUZNETSOV (skill `fst-project-health` / `figma-html-report-bridge`)
**Файл:** `references/view-filter-playbook.md`
**Связанный pitfall:** #13 в `mcp-server-probing`

---

## TL;DR

Некоторые MCP-серверы (PMForesight — live-probe 2026-08-08, обновлено 2026-08-22) поддерживают
передачу **фильтра в имени view** при вызове `get_view` через
`?<FieldName>=<value>`. Это работает как **server-side** фильтр и возвращает
**только нужные записи** — без пагинации, без локального фильтра,
в 10-1000× быстрее.

**Документация сервера НЕ перечисляет** поддерживаемые фильтры — единственный способ узнать — **live-probe каждого варианта**.

⚠️ **TRAP (live-probe 2026-08-22):** View может вернуть **статус 200 + данные**, но фильтр при этом **молча игнорируется** (возвращает те же данные для всех проектов). Всегда проверяйте **содержимое**, а не только наличие ответа!

---

## Где РАБОТАЕТ (live-probe PMForesight)

| View | Работающий фильтр | Сокращение | Live-probe дата |
|------|-------------------|-----------|-----------------|
| `Point/AllMyPoint` | `?ProjectId=<id>` | 702 → 34 | 2026-08-08 |
| `Project/ProjectBudgetCompleteBusiness` | `?ProjectId=<id>` | 2000+ → 12 | 2026-08-08 |
| **`Project/ProjectResourcePlan`** | **`?ProjectId=<id>`** | **2400+ → 149-2390 (только нужный проект)** | **2026-08-22 ✅** |
| **`Project/ProjectHealthCostMy`** | **`?ProjectId=<id>`** | **109 → 1 (только нужный проект)** | **2026-08-26 ✅ (ПОЧИНЕНО!)** |

## Где НЕ работает (live-probe PMForesight)

| View | Пробованный фильтр | Что вернулось | Live-probe |
|------|-------------------|----------------|------------|
| `Point/AllMyPoint` | `?ProjectCode=<code>` | 702 строк (все) | 2026-08-08 |
| `Point/AllMyPoint` | `?ParentCode=<code>` | 702 строк (все) | 2026-08-08 |
| **`Project/ProjectResourcePlan`** | **раньше: 2390 строк для всех** | **(поле `activityid` lowercase!)** | **resolved 2026-08-22** |
| `Project/MyProject` | `?ProjectId=<id>` | 10 строк (все) | 2026-08-08 |
| **`InContract/InContractMyProject`** | **`?ProjectId=<id>`** | **1 строка для 504-595; 0 строк для 503-434/503-152 (фильтр работает, но только для «своих» проектов)** | **2026-08-26 ⚠️ частично** |
| **`InContract` (без `MyProject`)** | **`?ProjectId=<id>`** | **42 строки (одинаковые для всех 3 проектов — фильтр не работает)** | **2026-08-26 ❌** |

---

## Как проверить (live-probe) — БЕЗОПАСНЫЙ паттерн

### Шаг 1: Probe разных вариантов фильтра

```bash
# Взять 3-4 варианта фильтра
for filter in "?ProjectId=3434" "?ActivityId=3434" "?ProjectCode=503-434" \
              "?ParentCode=503-434" "?projectid=3434"; do
    echo "=== ProjectHealthCostMy${filter} ==="
    python3 scripts/mcp_probe.py --tool get_view \
      --args "{\"entityName\":\"Project\",\"viewName\":\"ProjectHealthCostMy${filter}\",\"limit\":5}" 2>&1 | head -3
done
```

### Шаг 2: Проверить СТАТУС ОТВЕТА

| Что вернулось | Что значит |
|----------------|------------|
| **200, 0 rows** | Фильтр валидный, но данных нет для этого значения |
| **200, 50-500 rows, в ответе rows.filter(p == target) > 0** | **Фильтр работает ✅** |
| **200, 50-500 rows, в ответе rows.filter(p == target) == 0** | **TRAP: фильтр молча игнорируется, view возвращает данные для ВСЕХ проектов** ⚠️ |
| **500 — "operator does not exist: bigint = text"** | Формат параметра wrong — сервер не делает cast |
| **500 — "не удалось определить тип данных параметра $5"** | View поврежден / сломан разработчиками |
| **404 "Конечная точка не найдена"** | View не существует или фильтр не поддерживается |

### Шаг 3: КРИТИЧЕСКАЯ ПРОВЕРКА содержимого ⚠️

```python
def test_filter_works(view_name, filter_query, project_id, expected_field):
    """Проверяет что фильтр работает, а не просто возвращает данные."""
    sid, _ = mcp_init(client_name='probe-filter')
    r = mcp_call(sid, 'get_view', {
        'entityName': 'Project',
        'viewName': f'{view_name}{filter_query}',
        'limit': 200
    })
    rows = r.get('data', [])
    
    # 1. Подсчёт строк с целевым проектом
    matching = [row for row in rows if str(row.get(expected_field)) == str(project_id)]
    other = [row for row in rows if str(row.get(expected_field)) != str(project_id)]
    
    if other:
        # ⚠️ TRAP: фильтр НЕ работает
        print(f'❌ {view_name}{filter_query}: {len(matching)} правильных, {len(other)} чужих')
        return False
    
    # Проверка что вернули хотя бы что-то
    if not rows:
        print(f'⚠️ {view_name}{filter_query}: 0 строк (может быть ок, но нужна проверка данных)')
        return None  # inconclusive
    
    print(f'✅ {view_name}{filter_query}: {len(matching)} строк, все с project_id={project_id}')
    return True

# Использование:
test_filter_works('ProjectHealthCostMy', '?ProjectId=4595', 4595, 'projectid')
```

**Без этого теста легко принять фиктивный «успех»** — фильтр молча игнорирует параметр, сервер возвращает 200 OK + данные для ВСЕХ проектов.

---

## Что делать когда ничего не работает

### Вариант A: Fallback на пагинацию + локальный фильтр (pitfall #11)

```python
offset = 0
while offset < 600000:
    rows = mcp_call(sid, "get_view", {
        "entityName": "Project",
        "viewName": "ProjectHealthCostMy",
        "limit": 30000, "offset": offset,
    })
    if not rows: break
    proj_rows.extend(r for r in rows if r.get("projectid") == project_id)
    offset += len(rows)
    if len(rows) < 30000: break
```

### Вариант B: Открытый view вместо закрытого

```python
# InContractMyProject закрытый → 9 строк всегда одни и те же
# InContract открытый → 42 строки (но фильтр не работает)

# Решение: фильтровать по ParentFullName (pitfall #7 из fst-project-health)
contracts = mcp_call(sid, "get_view", {
    "entityName": "InContract", "viewName": "InContract",
    "limit": 500
})
proj_contracts = [c for c in contracts
                  if c.get("ParentFullName", "").startswith(f"{project_code}.")]
```

### Вариант C: Feedback разработчикам (pitfall #10)

Шаблон — `references/feedback-to-mcp-developers.md`. Включи таблицу выше и покажи **точный текст ошибки** (например, "500 - оператор не существует: bigint = text").

---

## Скрытые проблемы — что проявилось 2026-08-22

| # | Что случилось | Симптом | Урок |
|---|----------------|----------|------|
| 1 | `ProjectHealthCostMy?ProjectId=<id>` → 500 "bigint = text" (22.08) | Сервер принимает URL-параметр как **строку**, но PostgreSQL ожидает **bigint**. Сервер не делает cast. | **Перед тем как сообщать «фильтр работает»** — попробуй 2-3 типа данных: число (`4595`), строку (`"4595"`), float (`4595.0`). |
| 2 | `ProjectHealthCostMy` (без фильтра) → 500 (было 2000 строк) — 22.08 | **Сервер сломан** при попытке разработчиков добавить фильтр. **ПОЧИНЕНО 2026-08-26**: без фильтра возвращает 109 строк, с `?ProjectId=<id>` — 1 строку за 1.5 сек. | Документируй **дату** когда работало / сломалось. Это ключевая инфа для запроса к разработчикам. |
| 3 | `InContract?ProjectId=<id>` → 42 строки для всех 3 проектов (одинаковые) | **Фильтр игнорируется**, статус 200. | **Всегда проверяй содержимое**, не только статус. Без этого пропустишь TRAP. |
| 4 | `InContractMyProject?ProjectId=<id>` → 0 строк для 503-434/503-152 (1 для 504-595) | Серверная ошибка была 22.08, сейчас работает но только для «своих» проектов. Вероятно, фильтр по проекту + пользователю (нет доступа → 0 строк). | Документируй live-probe даты. Если фильтр частично работает — для production использовать `verify_filter_works()` для каждого проекта. |
| 5 | **ProjectHealthCostMy → ПОЧИНЕНО 2026-08-26** | Была регрессия 500 даже без фильтра. Разработчики починили за несколько дней. Pipeline `fst-project-health` ускорен с 60 до 19 сек (−68%) только за счёт этого фикса. | Документируй когда **починили** — фильтры могут сломаться снова. Перепроверяй при каждом запуске pipeline. |

---

## Связанные pitfalls

- **#11** (mcp-server-probing): Open views часто НЕ фильтруются по PK на сервере — нужна пагинация + локальный фильтр.
- **#12** (mcp-server-probing): Формат `activity_name` в open views — БЕЗ точки (`<code> `, не `<code>.`).
- **#10** (mcp-server-probing): Шаблон feedback-письма разработчикам MCP.
- **#13** (mcp-server-probing): Server-side фильтр `?FieldName=<value>` — основной.
- **#49, #50** (fst-project-health): Live-probe 504-595 → 149 строк с `?ProjectId=4595`. Раздел «Где работает» обновлён 2026-08-22 — `ProjectResourcePlan?ProjectId=` теперь подтверждён работающим.

---

## Обновления / changelog

| Дата | Что изменилось |
|------|----------------|
| 2026-08-21 | Первая версия — таблицы «работает/не работает» по live-probe 2026-08-08 |
| 2026-08-22 | **TRAP обнаружен**: фильтр может возвращать 200 OK + данные для ВСЕХ проектов (игнорирует параметр молча). Добавлен **Step 3: критическая проверка содержимого** с примером `test_filter_works()`. Добавлена колонка live-probe даты в таблицах. Добавлена секция «Скрытые проблемы» с примерами 2026-08-22 (`bigint = text`, сломанный `ProjectHealthCostMy`, игнорирование фильтра в `InContract`). |
| **2026-08-26** | **ProjectHealthCostMy починено разработчиками.** Live-probe подтвердил: `?ProjectId=4595` → 1 строка за 1.5 сек (было 41 сек). `ProjectResourcePlan?ProjectId=` работает (подтверждено 2026-08-22). Добавлены строки для починенных и частично работающих фильтров. Pipeline `fst-project-health` ускорен с 60 до 19 сек (−68%). **Правило:** при каждом запуске `verify_filter_works()` — фильтры могут сломаться снова. |
