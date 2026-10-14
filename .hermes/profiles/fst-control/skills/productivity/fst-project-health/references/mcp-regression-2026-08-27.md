# Регрессия MCP-фильтров от 2026-08-27

**Дата:** 2026-08-27
**Скилл:** `fst-project-health` v0.9.0+
**Автор:** ROSTISLAV KUZNETSOV (через Hermes-агент)
**Статус:** наблюдение, не баг-фикс

---

## Контекст

После успешного починения фильтра `ProjectHealthCostMy?ProjectId=<id>` (2026-08-26) разработчики MCP-сервера Форсайт сообщили о починке ещё двух проблем:
1. `InContract/InContractMyProject?ProjectId=<id>` — фильтр
2. Заполнение поля `projectid` в строках `InContract`

Live-probe 2026-08-27 показал, что **оба фикса фактически не работают** или привели к регрессии.

---

## Результаты live-probe 2026-08-27

### Тест 1: `InContractMyProject?ProjectId=<id>`

| Запрос | 2026-08-26 (до фикса) | 2026-08-27 (после фикса) |
|--------|------------------------|--------------------------|
| `InContractMyProject?ProjectId=4595` | **1 строка** ✅ (704-724 для 504-595) | ❌ **500 ошибка** |
| `InContractMyProject?ProjectId=3434` | 0 строк | ❌ **500 ошибка** |
| `InContractMyProject?ProjectId=3152` | 0 строк | ❌ **500 ошибка** |
| `InContractMyProject` (без фильтра) | 9 строк ✅ | 9 строк ✅ |

**Ошибка сервера:**

```
функция view_incontract_ofmyprojects(bigint, text) не существует
```

**Интерпретация:**
- Вчера для 504-595 возвращалась 1 строка (704-724).
- Сегодня — **500 Internal Server Error** для всех проектов.
- Похоже, что разработчики изменили сигнатуру функции (`view_incontract_ofmyprojects(bigint)` → `(bigint, text)`), но **не пересоздали саму функцию** в БД.

### Тест 2: `InContract/InContract?ProjectId=<id>` (без `MyProject`)

| Запрос | 2026-08-27 |
|--------|------------|
| `InContract?ProjectId=4595` | 42 строки (те же, что для всех) |
| `InContract?ProjectId=3434` | 42 строки (те же, что для всех) |
| `InContract?ProjectId=3152` | 42 строки (те же, что для всех) |
| `InContract` (без фильтра) | 42 строки |

**Поведение не изменилось.** Фильтр **по-прежнему не работает**.

### Тест 3: поле `projectid` в `InContract`

```json
{
  "id": 1,
  "InContractId": 1611,
  "Code": "701-611",
  "ParentFullName": "501-610. ФГК Сопровождение 2023-2026",
  "projectid": null
}
```

**`projectid: null` во всех 9 строках `InContractMyProject`.** Поле **не заполняется**.

### Тест 4: B-tree лимит 2704 (повторная проверка после "фикса")

| JSON | Размер | Размер индекса | Статус |
|------|-------:|---------------:|--------|
| `v0.1.0_504-595.json` | 5.2 КБ | (~2704) | ✅ OK |
| `v0.1.0_504-314.json` | 10.2 КБ | **3208** > 2704 | ❌ |
| `v0.1.0_503-434.json` | 12.7 КБ | **3544** > 2704 | ❌ |
| `v0.1.0_503-152.json` | 49.4 КБ | **8080** > 2704 | ❌ |

**Лимит НЕ изменился.** Ошибка: `размер строки индекса (8080) больше предельного для btree версии 4 размера (2704)`.

Сравнение с предыдущим live-probe (2026-08-22):

| Размер JSON | Индекс 2026-08-22 | Индекс 2026-08-27 | Изменилось? |
|------------:|------------------:|-------------------:|:-----------:|
| 12.5 КБ | 2992 | 3208 | ⚠️ +216 |
| 15.4 КБ | 3360 | 3544 | ⚠️ +184 |
| 59 КБ | 7792 | 8080 | ⚠️ +288 |

Размер индекса немного вырос (~200-300 байт). Возможно, добавили ещё поле в индекс, но **лимит 2704 остался**.

---

## Выводы

### Что **стало хуже**

- `InContractMyProject?ProjectId=<id>` — **регрессия** (был 1 строка для 504-595, теперь 500 ошибка).

### Что **не изменилось**

- `InContract?ProjectId=<id>` — фильтр не подключён.
- Поле `projectid` в InContract — пустое.
- B-tree лимит 2704 — не увеличен.

### На нашей стороне

- ✅ В скилле `fst-project-health` fallback через `ParentFullName.startswith()` остаётся рабочим.
- ✅ Не нужно ничего менять в `run_all.py` / `mcp_config.py` / `tests/`.
- ⏸️ Жду ответа разработчиков по фактическому статусу фикса.

---

## Что делать когда разработчики говорят "починили"

**Не верь на слово — проверь live.** Минимум два проекта через live probe:

```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "mcp_config",
    "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/mcp_config.py"
)
mcp_config = importlib.util.module_from_spec(spec)
sys.modules["mcp_config"] = mcp_config
spec.loader.exec_module(mcp_config)

sid, _ = mcp_config.mcp_init(client_name='probe-fix-verify')

for code, pid in [("504-595", 4595), ("503-434", 3434), ("503-152", 3152)]:
    r = mcp_config.mcp_call(sid, 'get_view', {
        'entityName': '...',
        'viewName': f'...?ProjectId={pid}',
        'limit': 100
    })
    rows = r.get('data', [])
    err = r.get('_error', '')[:120]
    print(f"{code}: rows={len(rows)} time=...")
    if err:
        print(f"  ❌ {err}")
    else:
        # Проверить что фильтр РЕАЛЬНО фильтрует
        # Например, для 503-434 — только договоры с projectid=3434
        for row in rows:
            assert row.get('projectid') == pid or '503-434' in (row.get('ParentFullName') or '')
```

**Чек-лист проверки:**

1. ✅ Запрос **не возвращает 500/400**.
2. ✅ Возвращает **меньше** строк, чем без фильтра (или 0 если ничего нет).
3. ✅ Возвращённые строки **реально** принадлежат запрошенному проекту (через `projectid` или `ParentFullName`).
4. ✅ Поле, о котором говорили разработчики (например `projectid`), **заполнено**.

---

## Что нужно писать в письме разработчикам когда регрессия

Структура (шаблон):

```
1. Что было ДО фикса (конкретные строки/числа)
2. Что стало ПОСЛЕ фикса (конкретные строки/числа)
3. Сравнительная таблица "до/после"
4. Конкретная ошибка сервера (первые 200 символов)
5. Скрипт для воспроизведения (копипаста)
6. Запрос: что прошу сделать
```

Пример — в `/root/.hermes/profiles/fst-control/cache/documents/Письмо_MCP_про_регрессию_InContractMyProject_2026_08_27.md`.

---

## Связанные pitfall'ы

- **Pitfall #50** (`references/forsight-mcp-quirks.md`) — `?ProjectId=<id>` server-side фильтр.
- **Pitfall #47** — DEPRECATED composite fetch (заменён на #50).
- **Bug #69** в `SKILL.md` — `importlib.util` не вызывает `main()` без явного вызова.

---

## Контакт

- **Telegram:** @kuznetsov-rostislav (или через Hermes-агент)
- **Дата:** 2026-08-27
- **Связанный skill:** `fst-project-health` v0.9.0+