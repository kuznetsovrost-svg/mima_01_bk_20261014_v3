# HTML-отчёт: pitfall-карта и recovery-рецепты

**Создан:** 2026-08-06 (накоплено за сессию по FIGMA → HTML для 504-595 / 503-152)

Это **сборник типичных ошибок** при генерации HTML-отчёта из MD-файла. Каждый pitfall содержит:
- Что сломалось (симптомы)
- Почему сломалось (корневая причина)
- Как починить (минимальный diff)
- Как **не** сломать снова (правило)

Используй как **чеклист** после каждой правки `scripts/build_html_report.py` или `templates/report.css`.

## Recovery-скрипт (запускать первым при поломке)

```bash
python3 -c "
from pathlib import Path
import re
html = Path('/tmp/project_504-595_report.html').read_text(encoding='utf-8')

# 1. CSS-правила
checks = {
    'сетка (border)':        'border: 1px solid #d1cfd7' in html,
    'подкраска critical':    '#fee2e2 !important' in html,
    'подкраска warning':     '#fef3c7 !important' in html,
    'индикатор синий фон':   '.report-indicator {' in html or 'report-indicator-circle' in html,
    'variant-tbl[open]':     'variant-tbl[open]' in html,
}
print('=== CSS ===')
for k, v in checks.items():
    print(f'  {\"✅\" if v else \"❌\"} {k}')

# 2. HTML-классы
print()
print('=== HTML ===')
tables = re.findall(r'<table[^>]*class=[\"\\']([^\"\\']+)[\"\\']', html)
for t in tables[:3]:
    has_tbl = t.startswith('tbl ') or t == 'tbl'
    print(f'  {\"✅\" if has_tbl else \"❌\"} {t}')

# 3. Подкраска строк
crit = len(re.findall(r'tr[^>]*status-critical', html))
warn = len(re.findall(r'tr[^>]*status-warning', html))
print(f'\\n=== Подкраска ===\\n  critical: {crit}, warning: {warn}')

# 4. Preview-логика
previews = re.findall(r'<span class=\"tbl-preview\">([^<]+)</span>', html)
print(f'\\n=== Preview ===')
for p in previews:
    bad = 'заполняется' in p.lower() or 'не пресейл' in p.lower()
    print(f'  {\"❌\" if bad else \"✅\"} {p}')
"
```

## Pitfall-карта (29 уникальных)

### P29. CSS-селектор `table.tbl` требует общего класса `tbl` на каждой таблице

**Симптом:** Сетка таблиц пропала (`border: 1px solid #d1cfd7` не применяется), подкраска строк не работает, хотя CSS-правила есть в `<style>`.

**Корневая причина:** Генератор выдаёт `<table class='tbl-kt'>` (только вариант-специфичный класс), но CSS-селекторы `table.tbl td { ... }` и `table.tbl tr.status-critical td { ... }` требуют **общего** класса `tbl`.

**Фикс:**
```python
# ❌ БЫЛО
out.append(f"<table class='{table_class}'>")

# ✅ СТАЛО
out.append(f"<table class='tbl {table_class}'>")
```

**Чек-лист:** `grep 'class="tbl tbl-' /tmp/project_*.html` — должно быть **5** таблиц (tbl-kt, tbl-overdue, tbl-completeness, tbl-finance, tbl-tech).

### P30. f-string с `{CSS}` ломает интерполяцию

**Симптом:** CSS-блок в `<style>` пустой, или HTML-файл меньше 10 КБ (должен быть ~11 КБ), или при открытии в браузере таблицы без стилей.

**Корневая причина:** В f-string `HTML = f"""... {CSS} ..."""` Python интерпретирует все `{` и `}` в `CSS` как f-string выражения. Если в CSS есть `.variant-tbl { ... }` — это ломается.

**Фикс:**
```python
# ❌ БЫЛО — f-string
HTML = f"""<!DOCTYPE html>
...
{CSS}
...
"""

# ✅ СТАЛО — обычная конкатенация
HTML_HEAD = """<!DOCTYPE html>
...
""" + CSS + """
...
"""
```

**Чек-лист:** `wc -c /tmp/project_*.html` — должно быть ≥ 10 000 байт.

### P31. Tuple unpacking bug при `*parse_md_table(...)` в `render_*(rows, columns)`

**Симптом:** В HTML таблице вместо данных — буквы «#», «Ц», «в», «т» в `<td>` ячейках.

**Корневая причина:** `parse_md_table()` возвращает `(headers, rows)`. Если сигнатура `render_tbl1_kt(rows, columns)` — то `*parse_md_table(...)` распаковывает headers в `rows` и rows в `columns`. Функция получает `rows = headers` (список из 9 названий колонок) и перебирает их как строки данных.

**Фикс:**
```python
# ❌ БЫЛО
content_3 = render_tbl1_kt(*parse_md_table(...))

# ✅ СТАЛО
content_3 = render_tbl1_kt(parse_md_table(...))  # функция принимает tuple
```

Или явно:
```python
h, r = parse_md_table(...)
content_3 = render_tbl1_kt(r, h)  # порядок явный
```

### P32. IndexError в `_filter_columns` при неполной MD-строке

**Симптом:** Скрипт падает с `IndexError: list index out of range` при сборке.

**Корневая причина:** MD-таблица может содержать строки с **меньшим** количеством колонок чем header (например, объединённые ячейки). При обращении `row[i]` где `i >= len(row)` — IndexError.

**Фикс:**
```python
# ❌ БЫЛО
new_row = [row[i] for i in col_indices]

# ✅ СТАЛО
new_row = [row[i] if i < len(row) else "" for i in col_indices]
```

### P33. Потеря достижений при рефакторинге CSS (без бэкапа)

**Симптом:** После «небольшого» рефакторинга CSS пропала сетка, подкраска строк, или синий фон индикатора. Пользователь говорит «всё сломалось».

**Корневая причина:** При объединении FIGMA-стилей с новыми — потерял 3 ключевых правила:
1. `border: 1px solid #d1cfd7` (сетка)
2. `#fee2e2 !important` (подкраска critical)
3. `!important` для перебивания `:nth-child(even)` zebra-striping

**Фикс (4-шаговый recovery-протокол):**
1. **Сделай бэкап ДО правки:** `cp templates/report.css /tmp/report.css.bak.$(date +%s)`
2. **Правь логическими секциями** (header, indicator, table, row-highlighting) — не всё сразу
3. **После каждой секции** — `diff /tmp/report.css.bak.* templates/report.css | head -50` — ищи потерянные правила
4. **Собери HTML** и проверь визуально что сетка/подкраска/индикатор работают

### P34. Подкраска строк не работает из-за zebra-striping `:nth-child(even)`

**Симптом:** Подкраска **визуально** пропадает на чётных строках, на нечётных — работает.

**Корневая причина:** CSS `table.tbl tr:nth-child(even) td { background: #fafafa }` перебивает `tr.status-critical td { background: #fee2e2 }` без `!important`.

**Фикс:** `!important` в правилах подкраски:
```css
table.tbl tr.status-critical td { background-color: #fee2e2 !important; }
table.tbl tr.status-warning td  { background-color: #fef3c7 !important; }
table.tbl tr.status-info td     { background-color: #f0fdf4 !important; }
```

### P35. FIGMA dot-classes в HTML требуют `[class~="..."]` в CSS

**Симптом:** Синий фон индикатора «Проект болен» не отображается, синяя панель header не отображается, хотя в HTML есть `<div class="report.project.indicator">` и в CSS есть `.report.project.indicator { background: #2563eb }`.

**Корневая причина:** В FIGMA-экспорте имена классов содержат точки: `<div class="report.project.indicator">`. В HTML `class="..."` — это **строка**, где точка — обычный символ. В CSS-селекторе `.report.project.indicator` интерпретируется как «элемент с **двумя** классами `report` и `project.indicator`», а не «один класс с точкой». Матч проваливается.

**Фикс (2 варианта):**
1. **Атрибутный селектор** — `[class~="report.project.indicator"]` (matches when class-атрибут **содержит** значение)
2. **Привести HTML к конвенциональному виду** — `<div class="report-indicator">` + `.report-indicator` в CSS

Рекомендация: **вариант 2** (конвенциональный) — проще, читаемее, не требует `[class~="..."]`-обёрток. Сохрани FIGMA-стили в `templates/report.css` через `[class~="..."]` для **обратной совместимости** (если HTML остаётся FIGMA-стилем), но в новых шаблонах используй конвенциональные классы.

### P36. tbl-tech захардкожен как «(Пресейл)» — данные не подставляются

**Симптом:** В HTML раздел 7 «Технические данные» — все 6 строк показывают «— (Пресейл) —» / «— нет данных —», хотя MD-раздел 7 содержит реальные значения.

**Корневая причина:** `render_tbl5_tech()` содержит хардкод:
```python
def render_tbl5_tech():
    out = []
    for n, name in [(1, "Пользователь"), ...]:
        out.append(f"<td>— (Пресейл)</td>")
```

**Фикс:** Читаем из MD, как для остальных таблиц:
```python
def render_tbl5_tech():
    sec7_text = extract_section(REPORT_MD, 7)
    rows_data = []
    for line in sec7_text.split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", line)
        if m and m.group(1).isdigit():
            rows_data.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    # ... рендер rows_data
```

**Правило:** `render_tbl5_tech()` и `render_tbl2_completeness()` заполняются **на ЛЮБОЙ стадии ЖЦ**. Это справочная информация (пользователь, MCP-сервер, версии) — она всегда доступна.

### P37. tbl-completeness захардкожен как «(Пресейл)» — данные не подставляются

**Симптом:** В HTML раздел 4 «Полнота заполнения» — все 5 строк показывают «— нет данных (Пресейл) —», хотя MD-раздел 4 содержит реальные данные.

**Корневая причина:** Аналогично P36 — `render_tbl2_completeness()` содержит хардкод для Пресейл.

**Фикс:** Читаем из MD, как для остальных таблиц.

**Правило:** Данные раздела 4 собираются **всегда** на **любой стадии ЖЦ**. Стадия влияет только на **интерпретацию** (pitfall #14), **не** на сбор. Сравни с P36 (tbl-tech) — тот же принцип.

### P38. Preview показывает хардкод «Заполняется на любой стадии ЖЦ»

**Симптом:** В `<summary class="tbl-preview">` для tbl-completeness или tbl-tech — текст «⚪ Заполняется на любой стадии ЖЦ» вместо итога проверки.

**Корневая причина:** Разработчик захардкодил **docstring-правило** в `preview_N`:
```python
preview_4 = "⚪ Заполняется на любой стадии ЖЦ"  # ❌ правило
```

**Фикс:** `preview_N` — это **итог проверки**, который берётся из MD через `_extract_preview()`:
```python
preview_4 = _extract_preview(extract_section(REPORT_MD, 4))  # ✅ итог
```

**Правило:** preview-логика **никогда** не должна хардкодить **правила разработки**. Только итоги проверки из MD.

### P39. Regex не ловит «Итог:» (без «по замечаниям»)

**Симптом:** Для раздела 6 (финансы) `preview_6` показывает только «Болен» без деталей. Пользователь спрашивает «где пояснения?».

**Корневая причина:** MD-раздел 6 содержит «**Итог:**» (короткий вариант), а regex `r"\*\*Итог по замечаниям:\*\*"` ловит только «Итог по замечаниям:» (длинный вариант).

**Фикс:** Regex с alternatives:
```python
m = re.search(r"\*\*(?:Итог по замечаниям|Итог):\*\*\s*(.+)", section_md)
```

### P40. Auto-fallback для preview когда «Итог» в MD отсутствует

**Симптом:** Для некоторых разделов (например, раздел 6 в проекте 503-152) MD содержит только «Статус раздела: БОЛЕН» без строки «Итог:». Тогда preview показывает только «БОЛЕН».

**Корневая причина:** `_extract_preview()` не имеет fallback когда summary не найдена.

**Фикс:** Добавить `_auto_summary()` который считает показатели «Да» и «Неопределено» в колонке «Результат»:
```python
def _auto_summary(section_md: str) -> str:
    n_critical = n_uncertain = 0
    for line in section_md.split("\n"):
        if "|" not in line: continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3: continue
        if cells[2] == "Да": n_critical += 1
        elif cells[2] == "Неопределено": n_uncertain += 1
    parts = []
    if n_critical: parts.append(f"{n_critical} показателей = «Да»")
    if n_uncertain: parts.append(f"{n_uncertain} «Неопределено»")
    return ", ".join(parts) if parts else "без замечаний"
```

### P41. Преамбула раздела в tbl-content «мусорит» над таблицей

**Симптом:** В развёрнутой `<details>` над таблицей показывается текст «Статус раздела: ...», «Цвет заголовка: ...», «Итог по замечаниям: ...» — как «мусор».

**Корневая причина:** `md_to_html()` не удаляет преамбулу — она попадает в `<div class="tbl-content">`.

**Фикс:** Удалять преамбулу ДО рендера:
```python
def md_to_html(md: str, table_class: str = "tbl") -> str:
    md = re.sub(r"\*\*Статус раздела:\*\*[^\n]*\n?", "", md)
    md = re.sub(r"\*\*Цвет заголовка:\*\*[^\n]*\n?", "", md)
    md = re.sub(r"\*\*Итог по замечаниям:\*\*[^\n]*\n?", "", md)
    md = md.lstrip("\n")
    # ... дальше рендер
```

**Правило:** Преамбула — в `<summary class="tbl-preview">`, **не** в `<div class="tbl-content">`.

### P42. `scripts/build_html_report.py` hardcoded на 504-595

**Симптом:** Запуск `python3 scripts/build_html_report.py` всегда собирает отчёт для 504-595. Для проекта 503-152 пришлось создать копию `/tmp/build_html_503_152.py`.

**Корневая причина:** Скрипт содержит `REPORT_MD = Path("/tmp/project_504-595_report.md")`.

**Фикс (TODO):** Сделать generic с CLI:
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--code", required=True)
args = parser.parse_args()
REPORT_MD = Path(f"/tmp/project_{args.code}_report.md").read_text(...)
```

**Workaround (на 2026-08-06):** `cp scripts/build_html_report.py /tmp/build_html_<code>.py` и заменить hardcoded путь.

## Recovery-чеклист (по приоритету)

| Приоритет | Действие | Симптом |
|-----------|----------|---------|
| 🔴 P29 | Проверить `<table class='tbl tbl-*'>` | Сетка и подкраска пропали |
| 🔴 P30 | Проверить `wc -c /tmp/project_*.html` ≥ 10 000 | HTML меньше 10 КБ, стили пустые |
| 🟡 P31 | Искать в HTML «#» в `<td>` первой строки | Буквы в данных |
| 🟡 P36/P37 | `grep "— (Пресейл)" /tmp/project_*.html` | Заглушки в tbl-tech/tbl-completeness |
| 🟡 P38 | Проверить preview на «Заполняется на любой стадии» | В preview правила вместо итогов |
| 🟢 P41 | Визуально проверить развёрнутую таблицу | Мусор над таблицей |

## Связанные документы

- `references/html-report-workflow.md` — пошаговый workflow (Шаги 0-11)
- `references/figma-to-html-recovery.md` — recovery-рецепты для FIGMA-экспорта
- `SKILL.md` pitfalls #17, #17a, #18, #19, #20, #21, #22, #23, #24, #25, #26, #27, #28 — основная pitfalls-карта

## Pitfall #44a. CSS-зрачок от inset shadow (round indicator)

**Симптом:** В цветном индикаторе (`.report-indicator-circle`) — тёмное пятно в центре. Пользователь: «убери тёмный кружок по центру».

**Корневая причина:** `box-shadow: inset 0 -8px 16px ...` + `inset 0 4px 8px ...` создают **«зрачок»** в центре круглого контейнера.

**Фикс:** Только внешняя тень:
```css
/* ❌ V2 — зрачок */
.report-indicator-circle {
    box-shadow: inset 0 -8px 16px rgba(0,0,0,.25),
                inset 0 4px 8px rgba(255,255,255,.4),
                0 4px 12px rgba(0,0,0,.2);
}
/* ✅ V3 — только внешняя */
.report-indicator-circle {
    box-shadow: 0 6px 16px rgba(0,0,0,.25),
                0 2px 4px rgba(0,0,0,.15);
}
```

## Pitfall #44b. Oval gradient от `circle at 30% 30%`

**Симптом:** Цветной градиент в круглом индикаторе **овальный**, хотя контейнер круглый.

**Корневая причина:** `radial-gradient(circle at 30% 30%, ...)` создаёт овальный градиент с центром в 30%30%.

**Фикс:** Симметричный градиент:
```css
/* ❌ V2 — овальный */
background: radial-gradient(circle at 30% 30%, ...);

/* ✅ V3 — круглый */
background: radial-gradient(circle at center, ...);
```

## Pitfall #44c. Round container растягивается без `!important`

**Симптом:** Цветной круг превратился в овал, контент текст растягивает контейнер.

**Корневая причина:** `width: 160px` (без `!important`) — текст внутри `<div>` растягивает контейнер.

**Фикс:** Зафиксировать все размеры:
```css
.report-indicator-circle {
    width: 160px !important;
    height: 160px !important;
    min-width: 160px; max-width: 160px;
    min-height: 160px; max-height: 160px;
    flex-shrink: 0;
}
```

## Pitfall #44d. Grid центрирует лучше flex для круглого контейнера

**Симптом:** В круглом индикаторе текст и эмодзи смещены вверх, не по центру.

**Корневая причина:** `display: flex; flex-direction: column` выравнивает контент в верхнюю часть flex-стэка.

**Фикс:** Grid с автоматическим делением на ряды:
```css
/* ❌ V3 — flex «прилипает» */
.report-indicator-circle {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

/* ✅ V4 — grid центрирует оба ряда */
.report-indicator-circle {
    display: grid;
    grid-template-rows: auto auto;
    align-content: center;
    justify-items: center;
}
```

## Pitfall #44e. Emoji-глиф 🔴 имеет тёмный «зрачок» — это не CSS

**Симптом:** После CSS-фикса (border, background, box-shadow) **тёмный «зрачок» в центре индикатора всё равно есть**. Пользователь: «Тёмный кружок по центру никуда не делся».

**Корневая причина:** Это **НЕ CSS**-проблема. Глиф эмодзи 🔴 в system-emoji шрифте содержит **тёмно-красный круг в центре** — это часть символа, не фон. `background: transparent` на div не делает глиф прозрачным.

**Фикс:** Убрать эмодзи из индикатора, оставить только текст:
```html
<!-- ❌ V4: эмодзи + текст (тёмный «зрачок» от эмодзи 🔴) -->
<div class="report-indicator-circle" data-status="sick">
    <div class="verdict-emoji">🔴</div>
    <div class="verdict-text">Проект болен</div>
</div>

<!-- ✅ V5: только текст -->
<div class="report-indicator-circle" data-status="sick">
    <div class="verdict-text">Проект болен</div>
</div>
```

**Правило:** Когда CSS-методы не убирают нежелательный визуальный артефакт — это **глиф самого символа**. Решение — убрать символ, текст оставить.

## Pitfall #44f. Indicator не помещается в grid-template-columns

**Симптом:** Цветной круг вылезает за правый край header'а.

**Корневая причина:** Header использует `grid-template-columns: 1fr 158px`, но круг 160px + padding 12px = 172px.

**Фикс:** Расширить колонку header:
```css
/* ❌ V3 — круг не помещается */
.report-header { grid-template-columns: 1fr 158px; }
.report-indicator { padding: 12px; min-height: 158px; }

/* ✅ V4 */
.report-header { grid-template-columns: 1fr 172px; }
.report-indicator { padding: 6px; min-height: 172px; }
```

## Pitfall #45. Hardcoded пути в скриптах = антипаттерн

**Симптом:** Скрипт всегда работает только для одного проекта. Для нового проекта — копируем и заменяем hardcoded пути.

**Корневая причина:** `REPORT_MD = Path("/tmp/project_504-595_report.md")` — literal value, не параметр.

**Фикс (V6):** Generic с CLI:
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--code", required=True, help="Project code, e.g. 504-595")
parser.add_argument("--output", help="Output HTML path")
parser.add_argument("--ls", action="store_true", help="List available projects")
args = parser.parse_args()
```

**Использование:**
```bash
python3 scripts/build_html_report.py --code 504-595
python3 scripts/build_html_report.py --code 503-152
python3 scripts/build_html_report.py --ls
```

**Чек-лист:** `grep -c 'project_504-595_report' scripts/build_html_report.py` — должно быть 0.

## Pitfall #46. Преамбула в tbl-content — мусор над таблицей

**Симптом:** В развёрнутой `<details>` над таблицей показывается «**Статус раздела:** Болен», «**Цвет заголовка:** Красный» — это «мусор» перед таблицей.

**Корневая причина:** `md_to_html()` не удаляет преамбулу — она попадает в `<div class="tbl-content">` ДО `<table>`.

**Фикс:** Удалять преамбулу ДО рендера. Преамбула — в `<summary class="tbl-preview">`, **не** в `<div class="tbl-content">`.

## Pitfall #47. Разовая имитация статуса без модификации скрипта

**Симптом:** Нужно проверить как выглядит индикатор с разными статусами (sick/attention/healthy), но не хочется трогать `scripts/build_html_report.py`.

**Техника:** Создать **отдельный скрипт** в `/tmp/`, который через regex временно подменяет «Статус раздела:» в MD и вызывает `build_html()`:

```python
import re
from pathlib import Path
import sys

sys.path.insert(0, '/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts')
import build_html_report as gen
import json

md = Path('/tmp/project_504-595_report.md').read_text()
project_data = json.loads(Path('/tmp/proj_504-595.json').read_text())

for new_status in ['Требует внимания', 'Здоров']:
    md_modified = re.sub(r'\*\*Статус раздела:\*\*\s*[^\n]+', f'**Статус раздела:** {new_status}', md)
    html = gen.build_html(md_modified, project_data)
    Path(f'/tmp/test_indicator_{new_status}.html').write_text(html, encoding='utf-8')
```

**Правило:** Для разовой диагностики — отдельный `/tmp/test_X.py`, **не** в `scripts/`.
