## Содержимое P44 — Цветной индикатор (data-status + radial-gradient)

### P44. Цветной индикатор статуса — `data-status` атрибут + radial-gradient

Если `report-indicator-circle` должен менять цвет по статусу (🔴 sick / 🟡 attention / 🟢 healthy / ⚪ unknown), **не используй разные классы** (`circle-sick`, `circle-attention`) — это плохо масштабируется. Используй **HTML data-атрибут**:

```html
<div class="report-indicator-circle" data-status="sick">🔴 Проект болен</div>
```

```css
.report-indicator-circle { background: radial-gradient(circle at 30% 30%, #d1d5db 0%, #9ca3af 40%, #6b7280 100%); }
.report-indicator-circle[data-status="sick"]      { background: radial-gradient(circle at 30% 30%, #fca5a5 0%, #ef4444 40%, #b91c1c 100%); }
.report-indicator-circle[data-status="attention"] { background: radial-gradient(circle at 30% 30%, #fde68a 0%, #f59e0b 40%, #b45309 100%); }
.report-indicator-circle[data-status="healthy"]   { background: radial-gradient(circle at 30% 30%, #86efac 0%, #22c55e 40%, #15803d 100%); }
```

**Рецепт выпуклости (3D-кнопка эффект):**
- radial-gradient с центром в `30% 30%` (имитация верхнего-левого блика)
- `inset 0 -8px 16px rgba(0,0,0,0.25)` — нижняя тень
- `inset 0 4px 8px rgba(255,255,255,0.4)` — верхний блик
- `0 4px 12px rgba(0,0,0,0.2)` — внешняя тень
- `text-shadow: 0 1px 2px rgba(0,0,0,0.4)` — тень текста
- `text-transform: uppercase` + `letter-spacing: 0.5px` — стильный заголовок

**Подстановка `data-status` в Python** — простая `.replace()` (НЕ f-string с CSS внутри, P30). Типичный паттерн: вычислить `_compute_verdict()` из статусов разделов 3/4/5/6, и подставить `verdict_status_class` в HTML.

**Чек-лист при поломке:** если круг индикатора не меняет цвет — проверить что (1) CSS содержит `data-status="sick"` правила, (2) HTML содержит `data-status="sick"` (или нужный) на `<div>`, (3) HTML правильно вложен в `<div class="report-indicator">` (родитель).

---

# ОРИГИНАЛЬНОЕ СОДЕРЖИМОЕ НИЖЕ

# HTML-отчёт: типичные ошибки и recovery-рецепты

**Создан:** 2026-08-06 (накоплено за сессию по FIGMA → HTML для 504-595 / 503-152)

Это **сборник типичных ошибок** при генерации HTML-отчёта из MD-файла. Используй как **чеклист** после каждой правки `scripts/build_html_report.py` или `templates/report.css`.

Подробности по каждому pitfall — в `references/html-report-workflow.md` (Шаги 0-11) и `references/html-report-pitfalls.md` (pitfalls #29-#42 + recovery-скрипт).

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
    'индикатор синий фон':   '.report-indicator {' in html,
    'variant-tbl[open]':     'variant-tbl[open]' in html,
}
print('=== CSS ===')
for k, v in checks.items():
    print(f'  {\"✅\" if v else \"❌\"} {k}')

# 2. HTML-классы
print('\\n=== HTML ===')
tables = re.findall(r'<table[^>]*class=[\"\\']([^\"\\']+)[\"\\']', html)
for t in tables[:3]:
    print(f'  {\"✅\" if t.startswith(\"tbl \") else \"❌\"} {t}')

# 3. Preview-логика (pitfall #27)
previews = re.findall(r'<span class=\"tbl-preview\">([^<]+)</span>', html)
print('\\n=== Preview ===')
for p in previews:
    bad = 'заполняется' in p.lower() or 'не пресейл' in p.lower()
    print(f'  {\"❌\" if bad else \"✅\"} {p}')
"
```

## Pitfall-карта (краткая)

### P29. CSS-селектор `table.tbl` требует общего класса `tbl` на каждой таблице

`<table class='tbl tbl-kt'>` (а не `<table class='tbl-kt'>`). Иначе CSS-правила для сетки и подкраски **не применятся**.

### P30. f-string с `{CSS}` ломает интерполяцию

CSS содержит `{` и `}` — Python интерпретирует их как f-string выражения. Использовать **конкатенацию** `HTML_HEAD + CSS + HTML_BODY` вместо `f"""... {CSS} ..."""`.

### P31. Tuple unpacking при `*parse_md_table(...)`

`parse_md_table()` возвращает `(headers, rows)`. Если сигнатура `render_tbl1_kt(rows, columns)` — `*` распаковывает headers в rows. **Передавать tuple без `*`**: `render_tbl1_kt(parse_md_table(...))`.

### P32. IndexError в `_filter_columns` при неполной MD-строке

MD может содержать строки с меньшим количеством колонок. Защита: `row[i] if i < len(row) else ""`.

### P33. Потеря достижений при рефакторинге CSS (без бэкапа)

4-шаговый recovery-протокол: (1) `cp templates/report.css /tmp/report.css.bak.<timestamp>`, (2) править по секциям, (3) `diff` после каждой, (4) визуально проверить.

### P34. Подкраска пропадает на чётных строках из-за `:nth-child(even)`

CSS zebra-striping перебивает `tr.status-critical td { background: #fee2e2 }`. Решение — `!important` в подкраске.

### P35. FIGMA dot-classes требуют `[class~="..."]` в CSS

`<div class="report.project.indicator">` — это **ОДИН** класс с точкой. CSS-селектор `.report.project.indicator` интерпретирует как два класса (через пробел). Решение: `[class~="report.project.indicator"]` или привести HTML к конвенциональному виду (`<div class="report-indicator">`).

### P36. tbl-tech захардкожен как «(Пресейл)» — данные не подставляются

`render_tbl5_tech()` не должен хардкодить заглушки. Данные **всегда** заполняются на любой стадии ЖЦ.

### P37. tbl-completeness захардкожен как «(Пресейл)» — данные не подставляются

Аналогично P36, для `render_tbl2_completeness()`. Данные **всегда** собираются.

### P38. Preview показывает хардкод «Заполняется на любой стадии ЖЦ»

`preview_N` — это **итог проверки** из MD, **не** правило разработки. Использовать `_extract_preview(section_md)`.

### P39. Regex не ловит «Итог:» (без «по замечаниям»)

`r"\*\*(?:Итог по замечаниям|Итог):\*\*"` — ловит оба варианта.

### P40. Auto-fallback для preview когда «Итог» в MD отсутствует

Если в MD нет строки «Итог:», `_auto_summary()` считает показатели «Да» и «Неопределено» в колонке «Результат».

### P41. Преамбула раздела в tbl-content «мусорит» над таблицей

Удалять `**Статус раздела:**` / `**Цвет заголовка:**` / `**Итог по замечаниям:**` **до** рендера. Они — в `<summary class="tbl-preview">`, не в `<div class="tbl-content">`.

### P42. `scripts/build_html_report.py` hardcoded на 504-595

TODO: переделать на CLI `python3 scripts/build_html_report.py --code <code>`. Workaround: `cp scripts/build_html_report.py /tmp/build_html_<code>.py` и заменить hardcoded путь.

## Связанные документы

- `references/html-report-pitfalls.md` — подробные pitfall-карты с минимальными diff-фиксами
- `references/html-report-workflow.md` — пошаговый workflow (Шаги 0-11)
- `references/figma-to-html-recovery.md` — recovery-рецепты для FIGMA-экспорта
- `SKILL.md` pitfalls #17, #17a, #18, #19, #20, #21, #22, #23, #24, #25, #26, #27, #28 — основная pitfalls-карта
