# `run_all.py` — Pitfalls, зафиксированные 2026-08-21/22

**Дата создания:** 2026-08-22
**Источник:** live-probe на 4 проектах (504-314, 503-434, 504-595, 503-152) после введения `run_all.py` как единого оркестратора.

Этот документ **расширяет** основной `SKILL.md` и `references/forsight-mcp-quirks.md` — здесь собраны баги **специфичные для `run_all.py`** и парсинга MD → HTML.

---

## Главный урок (live-probe 2026-08-22, подтверждённый пользователем)

> «Исправь генерацию HTML, а не только этот отчет - эти ошибки повторяются и на других проектах»

Когда пользователь жалуется на HTML — **всегда** смотри на **генератор** (`build_html_report.py` / `templates/report.css` / `run_all.py`), а не на конкретный отчёт. Один фикс в генераторе = N починок в отчётах.

**Доказательство:** 5 багов в `build_html_report.py` (одна итерация) — все 4 проекта (504-314, 503-434, 504-595, 503-152) получили корректные отчёты.

---

## Bug #70 — `compute_verdict` искал `**Статус раздела:**`

**Симптом:** Indicator всегда серый «Нет данных» (`data-status="unknown"`) независимо от состояния разделов 3-6.

**Корень:** В `build_html_report.py:261` regex `r"\*\*Статус раздела:\*\*\s*(.+)"` — никогда не находил, потому что `run_all.py` пишет `**Вердикт раздела:**`.

**Фикс:** Альтернатива в regex:
```python
m = re.search(r"\*\*(?:Вердикт|Статус) раздела:\*\*\s*(.+)", sec)
```

**Чек-лист:**
```bash
python3 scripts/run_all.py --code 504-314 --no-word
grep 'data-status=' /tmp/project_504-314_report.html | head -3
# Должно быть НЕ "data-status=\"unknown\"", а "sick"/"attention"/"healthy"
```

**Регрессионный тест:** покрывается через Bug #71-#73 (HTML structure).

---

## Bug #71 — `status_class()` не понимал «Синий» / «Желтый»

**Симптом:** Подсветка строк (`status-warning`/`status-info`/`status-critical`) не срабатывала. `grep -c 'status-warning\|status-info\|status-critical' /tmp/project_<code>_report.html` возвращал 0.

**Корень:** В `status_class()`:
```python
if "существен" in s or "жёлт" in s or "🟡" in status_text:
```
Только «жёлт» (с ё). В MD `run_all.py` пишет «Желтый» (с е). Не срабатывает.

**Фикс:** Оба варианта:
```python
if "существен" in s or "жёлт" in s or "желт" in s or "🟡" in status_text:
    return "status-warning"
if "информацион" in s or "синий" in s or "⚪" in status_text or "норма" in s:
    return "status-info"
```

**Чек-лист:**
```bash
grep -c 'status-warning\|status-info\|status-critical' /tmp/project_<code>_report.html
# Должно быть >= 6 (по 3 на разделы 3, 5, 6)
```

**Регрессионный тест:** `tests/test_helpers.py::TestMcpConfigHelpers::test_status_class_recognizes_colors` — проверяет 7 вариантов ("Синий", "Желтый", "Жёлтый", "Красный", "критическое", "существенное", "информационное").

---

## Bug #72 — `render_tbl3_overdue()` использовал неверные индексы колонок

**Симптом:** Колонка «Код» показывала «Информационное», «Название» — реальные КТ-коды.

**Корень:** MD раздела 5 от `run_all.py` имеет 8 колонок:
```
r[0]=#, r[1]=Цвет, r[2]=Статус, r[3]=Код КТ, r[4]=Название, r[5]=План, r[6]=Прогноз, r[7]=Дней
```

Старый код использовал `r[2]` для Код (реально это Статус), `r[3]` для Название (реально Код КТ).

**Фикс:**
```python
out.append(f"<td>{r[3] if len(r) > 3 else ''}</td>")  # Код КТ
out.append(f"<td>{r[4] if len(r) > 4 else ''}</td>")  # Название
out.append(f"<td>{r[5] if len(r) > 5 else ''}</td>")  # План
out.append(f"<td>{r[6] if len(r) > 6 else ''}</td>")  # Прогноз
```

**Чек-лист:** Просмотреть `/tmp/project_<code>_report.html` раздел 5 — в колонке «Код» должны быть `104-XXX`, а не «Информационное».

---

## Bug #73 — `get_metamodel_metadata()` — неверные ключи в `build_section_7()`

**Симптом:** Раздел 7 (Технические данные) — все значения в колонке «Значение» = `—`.

**Корень:** `build_section_7()` в `run_all.py` использовал ключи `user`, `metamodel_title`, `metamodel_core_version`, `server_name`, `server_version`. Реальные ключи из `get_metamodel_metadata()`: `title`, `version`, `core_version`.

**Фикс:**
```python
data.get('title') or '—'         # было data.get('metamodel_title', '—')
data.get('version') or '—'       # было data.get('server_version', '—')
data.get('core_version') or '—'  # было data.get('metamodel_core_version', '—')
# URL берём из mcp_config.MCP_URL, не из MetaModel
MCP_URL
```

**Чек-лист:**
```bash
grep -A 1 'Значение' /tmp/project_<code>_report.html | grep -v '—'
# Должно быть 3 непустых значения (Title, CoreVersion, Version)
```

**Регрессионный тест:** покрывается через Bug #74 (budget).

---

## Bug #74 — `ProjectBudgetSummary.contract_count` не атрибут dataclass

**Симптом:** В разделе 4 показатель 5 «Корректность графика платежей» — `Ошибка: 'ProjectBudgetSummary' object has no attribute 'contract_count'`.

**Корень:** `contract_count` существует только как ключ в `to_dict()`, но не как атрибут dataclass. В dataclass есть `contract_ids: set[int]`.

**Фикс:**
```python
contract_count = len(budget_summary.contract_ids)
# вместо
budget_summary.contract_count
```

**Чек-лист:**
```bash
grep 'Ошибка' /tmp/project_<code>_report.md
# Должно быть пусто
```

**Регрессионный тест:** `tests/test_helpers.py::TestMcpConfigHelpers::test_budget_summary_contract_count` — проверяет, что `contract_count` НЕ атрибут, а `contract_ids` — есть.

---

## Bug #75 — `build_section_3/5` — неправильная классификация (diff vs overdue)

**Симптом:** «Много строк имеют просрочку выше критической, но строка остаётся информационной» (пользователь, 2026-08-21). PlanDate=2026-06-12 (сегодня 2026-08-21 = 70 дней просрочки) с forecast=2026-06-15 (diff=+3) классифицировалось как «Информационное».

**Корень:** Классификация использовала ТОЛЬКО `diff = forecast - plan`, а НЕ реальную просрочку от сегодня.

**Фикс:** Добавить `overdue_days = max(0, (today - pd).days) if pd < today else 0`:
```python
if overdue_days >= 30 or abs_diff > thr_remark.REMARK_THRESHOLDS["critical"]["min_diff_days"]:
    color, status = "Красный", "Критическое"
elif overdue_days >= 14 or abs_diff > thr_remark.REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
    color, status = "Желтый", "Существенное"
```

**Применяется в:** `build_section_3()` (раздел 3, замечания по срокам).

---

## Bug #76 — `tbl-finance td { height: 70px }`

**Симптом:** В разделе 6 (Финансы) между строками огромные пустоты (~70px).

**Корень:** В `templates/report.css` — слишком большая высота строк финансовой таблицы.

**Фикс:**
```css
table.tbl-finance td {
    height: 40px;  /* было 70px */
    vertical-align: middle;  /* было top */
    padding-top: 4px;  /* было 10px */
}
```

**Чек-лист:** Визуально — строки финансов должны быть компактными, как в других таблицах.

---

## Bug #77 — `tbl-overdue td { white-space: nowrap }`

**Симптом (пользователь, 2026-08-21):** «Разделе «Актуальность прогноза по проекту» должен быть перенос слов в длинных наименованиях на новую строку как в разделе с контролем сроков!»

**Корень:** В `templates/report.css`:
```css
table.tbl-overdue td { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
```

Было добавлено чтобы даты не переносились — но это убивает перенос длинных названий КТ.

**Фикс:**
```css
table.tbl-overdue td { word-wrap: break-word; overflow-wrap: break-word; }
```

Узкие колонки (140px) для дат и просрочки удерживают их на одной строке сами по себе.

**Чек-лист:**
```bash
grep 'tbl-overdue' /tmp/project_<code>_report.html | grep 'nowrap'
# Должно быть пусто
```

**Регрессионный тест:** `tests/test_skill_md_integrity.py::TestSkillMdIntegrity::test_tbl_overdue_wraps_long_text`.

---

## Bug #78 — `tbl-kt` без ширин колонок

**Симптом (пользователь, 2026-08-22):** «значения в Колонках "код", "План" и "прогноз" не умещаются. И в поле "Наименование" нет переноса по словам».

**Корень:** В `templates/report.css` для `tbl-kt` была задана только `height: 30px`, без `width` для колонок (в отличие от `tbl-overdue`, где уже был фикс для Bug #77).

**Фикс:**
```css
table.tbl-kt th:nth-child(1), table.tbl-kt td:nth-child(1) { width: 40px; }   /* # */
table.tbl-kt th:nth-child(2), table.tbl-kt td:nth-child(2) { width: 90px; }   /* Код */
table.tbl-kt th:nth-child(3), table.tbl-kt td:nth-child(3) { width: 552px; }  /* Наименование */
table.tbl-kt th:nth-child(4), table.tbl-kt td:nth-child(4) { width: 110px; }  /* План */
table.tbl-kt th:nth-child(5), table.tbl-kt td:nth-child(5) { width: 110px; }  /* Прогноз */
table.tbl-kt td { word-wrap: break-word; overflow-wrap: break-word; }
```

**Чек-лист:** Визуально — даты 2026-08-13 помещаются в 110px, названия КТ переносятся.

**Регрессионный тест:** `tests/test_skill_md_integrity.py::TestSkillMdIntegrity::test_tbl_kt_has_column_widths` (проверяет ширины >= 110px для План/Прогноз, >= 400px для Наименование, наличие `word-wrap: break-word`).

---

## Hard rule — forecast vs plan (пользователь, 2026-08-21)

**Формулировка пользователя (canonical):**
> - Актуальность прогнозов проверяется на сравнении **прогнозной даты** и текущего момента.
> - Если прогнозная дата ещё не наступила — строка вообще никакой просрочки не имеет.
> - Такую строку **не нужно даже выводить** в таблицу.
> - Размер просрочки измеряется как разница между **прогнозной датой** и текущей датой и никак иначе.
> - Просрочка — это если срок прогноза уже прошёл, а КТ или работа **не закрыты фактической датой**.

**Эта формулировка переопределяет первоначальную (неправильную) логику**, которая считала просрочку от PlanDate. После пользовательской коррекции — **только от ForecastDate**, **только в разделе 5** (build_section_5).

**Реализация в `build_section_5()`:**
```python
for p in project_points:
    pd = parse_date(p.get("PlanDate"))   # НЕ используется для просрочки
    fd = parse_date(p.get("ForecastDate"))
    fact = parse_date(p.get("FactDate"))

    if fact: continue           # Закрыта факт → не показываем
    if not fd: continue         # Нет прогноза → не показываем
    if fd >= today: continue    # Прогноз в будущем → НЕ выводить

    overdue_days = (today - fd).days
    cls = classify_relevance(overdue_days)
```

**Раздел 3 vs раздел 5 (разная семантика!):**
- **Раздел 3** (`build_section_3`) — «Замечания по срокам»: КТ у которых `forecast != plan`. Без проверки просрочки от сегодня.
- **Раздел 5** (`build_section_5`) — «Актуальность прогнозов»: ТОЛЬКО КТ у которых `forecast < today` И `fact IS NULL`.

**Регрессионный тест:** `awk '/## 5/,/## 6/' /tmp/project_503-434_report.md | grep -E 'forecast.*2026-08-3[0-9]'` — должно быть **пусто** (forecast в будущем не попадает).

---

## Универсальный паттерн: каждая таблица должна иметь

Каждая таблица отчёта (`tbl-kt`, `tbl-overdue`, `tbl-finance`, `tbl-completeness`, `tbl-tech`) ДОЛЖНА иметь:

1. **Фиксированные ширины колонок** через `nth-child(N)`.
2. `word-wrap: break-word` для переноса длинных наименований.
3. Достаточную ширину для дат `YYYY-MM-DD` (>= 100px).
4. Достаточную ширину для названий КТ/проектов (>= 400px).

**Чек-лист при добавлении новой таблицы:**
```bash
# 1. У всех колонок есть явная width?
grep -A 30 "table.tbl-NEW-CLASS" templates/report.css | grep "nth-child"

# 2. Есть word-wrap для ячеек?
grep -A 30 "table.tbl-NEW-CLASS" templates/report.css | grep "word-wrap"

# 3. Тесты проходят?
cd tests && python3 run_all_tests.py
```

---

## Workflow правила (дополнение к основному SKILL.md)

### Правило #1: Fix the generator, not the output

Когда пользователь жалуется на HTML/MD-отчёт, **всегда** смотри на генератор. Один фикс в генераторе = N починок в отчётах.

**Контр-пример:** открыть `/tmp/project_504-314_report.html`, найти кривые колонки, сделать `patch` строк в HTML — это не решает проблему для 504-595, 503-152.

### Правило #2: Don't claim "fixed" without verification

After any change to `scripts/build_html_report.py`, `scripts/run_all.py`, `templates/*`:

1. `cd tests && python3 run_all_tests.py --report` → must be 6/6 PASS.
2. `python3 scripts/run_all.py --code 504-314 --no-word --timing` → must produce HTML + MD without `RuntimeError`.
3. `grep 'data-status=' /tmp/project_504-314_report.html` → must NOT be `data-status="unknown"`.
4. `grep -c 'status-warning\|status-info\|status-critical' /tmp/project_504-314_report.html` → must be >= 8.

**Don't tell the user "готово ✅" until all 4 pass.**

### Правило #3: 5-7 системных багов = в одну итерацию

5 багов #70-#74 были исправлены за одну сессию (2026-08-21). Признак того, что это **системная проблема**, а не одиночный баг:
- Баг проявляется на **нескольких проектах** (>= 2)
- Баг связан с **генератором** (а не с данными конкретного проекта)
- Баг затрагивает **несколько** секций отчёта одновременно

Если видишь 1 баг — фикс локальный. Если видишь **3+ связанных бага** в одной области (например, всё в `build_html_report.py`) — это **системная проблема**, чини сразу всё что видишь.

### Правило #4: Регрессионные тесты на каждый баг

Каждый Bug #70-#78 имеет **регрессионный тест** в `tests/`. При добавлении нового бага:
1. Напиши регрессионный тест **до** фикса (TDD).
2. Проверь что тест падает.
3. Сделай фикс.
4. Проверь что тест проходит.
5. Все 6 тестов (39+ подтестов) — 6/6 PASS.

---

## Сводка: 5+ ключевых bug + 1 hard rule

| # | Bug | Severity | Где | Тест |
|---|-----|----------|-----|------|
| 70 | compute_verdict regex | High (indicator сломан) | `build_html_report.py:261` | Bug 71 регрессия |
| 71 | status_class ё/е | High (нет подсветки) | `build_html_report.py:118` | `test_status_class_recognizes_colors` |
| 72 | render_tbl3_overdue индексы | High (неверные данные) | `build_html_report.py:187` | ручной чеклист |
| 73 | get_metamodel keys | Medium (пустой раздел 7) | `run_all.py:530` | Bug 74 регрессия |
| 74 | contract_count атрибут | High (ошибка в отчёте) | `run_all.py:310` | `test_budget_summary_contract_count` |
| 75 | overdue vs diff_days | High (неверная классификация) | `run_all.py:188, 391` | ручной чеклист |
| 76 | tbl-finance height=70px | Low (визуал) | `templates/report.css:266` | ручной чеклист |
| 77 | tbl-overdue nowrap | High (нет переноса) | `templates/report.css:266` | `test_tbl_overdue_wraps_long_text` |
| 78 | tbl-kt no widths | High (колонки не помещаются) | `templates/report.css:247` | `test_tbl_kt_has_column_widths` |
| **HR** | **forecast vs plan** | **Critical** (семантика) | **`build_section_5`** | **`build_section_5` регрессия** |

**Ключевой hard rule:** forecast vs plan (canonical формулировка пользователя 2026-08-21).

---

## Связь с другими документами

- **Основной SKILL.md** — Live-bugs #64-#69 (run_all.py), #70-#78 (MD→HTML несоответствие).
- **`references/forsight-mcp-quirks.md`** — MCP-quirks (parentfullname, encoding, фильтры).
- **`references/md-report-conventions.md`** — шаблоны MD для 5 разделов, что можно/нельзя в значениях таблиц.
- **`references/test-procedure.md`** — процедура self-тестирования, 6 файлов за 1.3 сек.
- **`references/run-all-procedure.md`** — полная инструкция по `run_all.py`, 9 live-bugs.
- **`references/mcp-server-filter-playbook.md`** — запросы к разработчикам MCP на server-side фильтры.

