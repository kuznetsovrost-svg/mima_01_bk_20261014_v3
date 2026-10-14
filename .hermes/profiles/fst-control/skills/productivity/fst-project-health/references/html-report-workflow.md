# Workflow: генерация HTML-отчёта из MD через FIGMA-макет

**Обновлён:** 2026-08-06 (добавлены секции про preview-логику, hardcoded-скрипт, правила стадии ЖЦ)
**Источник:** сессия по сборке FIGMA → HTML для проектов 504-595 и 503-152

## Назначение

Когда пользователь присылает FIGMA-эскиз + HTML-каркас + CSS (или просто хочет красивый HTML-отчёт), у скилла есть готовый workflow для генерации `project_<code>_report.html`.

## Шаг 0: получить эталон

Перед правкой CSS — **сохрани текущий рабочий HTML** в `/tmp/report_<timestamp>.html`. Если сломаешь, откатывайся через diff.

## Шаг 1: распаковать FIGMA (если есть)

`.fig` файл — это **ZIP-архив**:

```bash
mkdir /tmp/figma_extract
cd /tmp/figma_extract
unzip -q -o <путь-к-.fig>
ls
# canvas.fig, thumbnail.png, meta.json, images/
```

`canvas.fig` — бинарный, **не читается как текст**. Но `meta.json` может дать представление о дизайне.

## Шаг 2: понять что FIGMA-экспорт содержит мусор

FIGMA-экспорт → HTML содержит три типичных артефакта (см. pitfalls #17, #17a, #18):

1. `position:absolute` для всех элементов (наследие FIGMA canvas)
2. `cols1...colsN` для каждой ячейки таблицы (вместо нормальной `<table>`)
3. FIGMA-классы с точками: `<div class="report.header">` — это **ОДИН** класс с точкой, не два
4. Сетка в качестве визуальной подсказки (НЕ часть дизайна)

## Шаг 3: извлечь из FIGMA **только**:

- **Палитру цветов**: `#dbeafe` (фон), `#2563eb` (header), `#d1cfd7` (collapsed), `#f7f7fa` (ячейка), `#232326` (текст), `#fee2e2/#fef3c7/#f0fdf4` (подкраска строк)
- **Шрифт**: Open Sans, размеры 11-15px
- **Иерархию элементов**: header (2 колонки), 5 таблиц-открывашек (collapsible), footer
- **Состав таблиц**: какие колонки, какие плейсхолдеры — **сверять с `tblX.html`**
- **Высоту строк**: tbl1/tbl2/tbl3/tbl5 = 30px, tbl4 = 70px

## Шаг 4: написать production CSS

Создать `templates/report.css`:
- `@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap');`
- `body { font-family: 'Open Sans', sans-serif; background: #dbeafe; padding: 24px; }`
- `.report-container { max-width: 920px; margin: 0 auto; background: #dbeafe; }`
- `.report-header { display: grid; grid-template-columns: 1fr 158px; }` — **конвенциональный** класс (без точки!)
- `.report-indicator { background: #2563eb; }`
- `.report-indicator-circle { background: #fff; border-radius: 50%; width: 136px; height: 136px; }`
- `.variant-tbl { background: #fff; border-radius: 8px; overflow: hidden; }`
- `.variant-tbl > summary { background: #d1cfd7; padding: 8px 14px; cursor: pointer; }`
- `.variant-tbl[open] > summary::after { transform: rotate(180deg); }`
- `table.tbl { border-collapse: collapse; width: 100%; font-size: 12px; color: #232326; }`
- **`table.tbl td { padding: 6px 10px; border: 1px solid #d1cfd7; }`** ← КРИТИЧНО (сетка)
- **`table.tbl tr.status-critical td { background-color: #fee2e2 !important; font-weight: 700; }`** ← КРИТИЧНО (подкраска)
- **`table.tbl tr.status-warning td { background-color: #fef3c7 !important; }`** ← КРИТИЧНО (подкраска)
- `table.tbl tr.status-info td { background-color: #f0fdf4 !important; }`
- `table.tbl-kt th, table.tbl-kt td { height: 30px; }` ← Вариант-специфичные высоты
- `table.tbl-finance td { height: 70px; vertical-align: top; padding-top: 10px; }`

## Шаг 5: написать production HTML

Создать `templates/report.html`:
- Конвенциональные классы (`report-header`, `report-indicator`, `tbl-content`)
- `<details class="variant-tbl" open>` для каждой таблицы (первая — открыта)
- `<summary>` с двумя `<span>`: имя + preview
- `<div class="tbl-content">{{ section_N_content }}</div>` — **только таблица**, без преамбулы

### КРИТИЧНО: не показывай преамбулу раздела внутри `<details>`

Преамбула (`Статус раздела:`, `Цвет заголовка:`, `Итог по замечаниям:`) должна быть **в preview-bar**, а не внутри раскрытой таблицы. Иначе пользователь видит «мусор» над таблицей.

```python
# В build_html_report.py — удаляй преамбулу из tbl-content:
md = re.sub(r"\*\*Статус раздела:\*\*[^\n]*\n?", "", md)
md = re.sub(r"\*\*Цвет заголовка:\*\*[^\n]*\n?", "", md)
md = re.sub(r"\*\*Итог по замечаниям:\*\*[^\n]*\n?", "", md)
```

## Шаг 6: COLUMN_MAP в скрипте

MD-таблицы содержат **лишние колонки** (`Цвет`, `Статус`, `Факт`) которые FIGMA НЕ показывает. Без маппинга в HTML попадают все 9 колонок → отчёт «поломан» (лишние колонки, широкие/неверные ширины).

```python
COLUMN_MAP = {
    "tbl-kt":          [0, 3, 4, 5, 6, 8],          # 6 колонок: #, Код, Наименование, План, Прогноз, Исполнитель
    "tbl-overdue":     [0, 2, 3, 4, 5, 7],          # 6 колонок: #, Код, Название, План, Прогноз, Просрочка
    "tbl-completeness": [0, 1, 2],                  # 3 колонки: #, Показатель, Результат
    "tbl-finance":     [0, 1, 2],                  # 3 колонки: #, Показатель, Результат
    "tbl-tech":        [0, 1, 2],                  # 3 колонки: #, Показатель, Значение
}
```

Структура MD-таблиц (найдено эмпирически 2026-08-06):
- tbl1 (раздел 3): `[#, Цвет, Статус, Код, Наименование, План, Прогноз, Факт, Исполнитель]` → FIGMA: 6 колонок
- tbl3 (раздел 5): `[#, Цвет, Код КТ, Название, План, Прогноз, Факт, Дней просрочки, Статус, Исполнитель]` → FIGMA: 6 колонок
- tbl2 (раздел 4): `[#, Показатель, Результат, Детализация, Статус]` → FIGMA: 3 колонки (Детализация → Результат)
- tbl4 (раздел 6): `[#, Показатель, Результат, Детализация]` → FIGMA: 3 колонки (Детализация → Результат)
- tbl5 (раздел 7): `[#, Показатель, Значение]` → FIGMA: 3 колонки

## Шаг 7: preview-логика (НЕ хардкод итога проверки!)

`<summary class="tbl-preview">` показывает **итог проверки** — **не** хардкод правил разработки.

### Что читаем из MD

```python
def _extract_preview(section_md: str) -> str:
    """Берёт «Статус раздела:» + «Итог по замечаниям:» (или «Итог:») из MD."""
    status = ""
    summary = ""
    m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", section_md)
    if m: status = m.group(1).strip()
    # Regex ловит ОБА варианта: «Итог по замечаниям:» и «Итог:» (финансы)
    m = re.search(r"\*\*(?:Итог по замечаниям|Итог):\*\*\s*(.+)", section_md)
    if m: summary = m.group(1).strip()
    # Auto-fallback: если «Итог» в MD нет, вычисляем из таблицы
    if not summary: summary = _auto_summary(section_md)
    return f"{status} — {summary}" if status and summary else status or "Нет данных"
```

### Auto-fallback для preview

Если в MD нет строки «Итог:» (например, для проекта 503-152 в разделе 6), `_auto_summary()` считает показатели «Да» и «Неопределено» в колонке «Результат»:

```python
def _auto_summary(section_md: str) -> str:
    """Считает «Да» (критично) и «Неопределено» (тревожно) в таблице показателей."""
    n_critical = n_uncertain = 0
    for line in section_md.split("\n"):
        if "|" not in line: continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3: continue
        # cells[0]=#, cells[1]=Показатель, cells[2]=Результат
        if cells[2] == "Да": n_critical += 1
        elif cells[2] == "Неопределено": n_uncertain += 1
    parts = []
    if n_critical: parts.append(f"{n_critical} показателей = «Да»")
    if n_uncertain: parts.append(f"{n_uncertain} «Неопределено»")
    return ", ".join(parts) if parts else "без замечаний"
```

### Что НЕ писать в preview

- ❌ `"⚪ Заполняется на любой стадии ЖЦ"` — это **правило разработки**, не итог проверки.
- ❌ `"🔴 Болен — 2 критических КТ"` — это **захардкоженный** итог, который устареет при изменении данных.
- ✅ `"Болен — 69 критических, 9 существенных, 5 информационных"` — итог из MD.
- ✅ `"Нейтральный — справочная информация"` — для tbl-tech (там нет «Статус раздела:»).

## Шаг 8: правила стадии ЖЦ

### tbl-tech (раздел 7) и tbl-completeness (раздел 4) — ВСЕГДА заполняются

**Пресейл — не причина для заглушек.** Данные собираются на **любой стадии ЖЦ**. Стадия влияет только на **интерпретацию** (pitfall #14: какой показатель «легитимно = Нет» на Пресейл), **не** на сбор.

```python
def render_tbl5_tech():
    """tbl5: тех. данные (6 показателей).

    ⚠️ ВАЖНО: данные должны заполняться **на любой стадии ЖЦ**, включая Пресейл.
    """
    sec7_text = extract_section(REPORT_MD, 7)
    # ... читаем из MD, не хардкодим
```

```python
def render_tbl2_completeness():
    """tbl2: полнота заполнения (5 показателей).

    ⚠️ ВАЖНО: данные должны заполняться **на любой стадии ЖЦ**, включая Пресейл.
    Стадия ЖЦ влияет только на **интерпретацию** (pitfall #14).
    """
    # Аналогично — читаем из MD
```

### tbl4 (раздел 6 финансы) — обычно заполняется с Пресейл

Для проекта 503-152 (Пресейл) — финансы **уже заложены** (forecast = −37.5 млн ₽). `render_tbl4_finance()` читает из MD — `ProjectHealthCostMy` view возвращает данные даже на Пресейл.

### Чек-лист проверки

```bash
# Если в HTML для tbl-tech или tbl-completeness видишь «— (Пресейл) —» в КАЖДОЙ строке — это ошибка
grep "— (Пресейл)" /tmp/project_*.html
# Должно быть пусто!
```

## Шаг 9: критичные правила генератора

### НИКОГДА не используй `*` для распаковки tuple

```python
# ❌ НЕПРАВИЛЬНО — сигнатура (rows, columns), а *parse_md_table даёт (headers, rows)
content_3 = render_tbl1_kt(*parse_md_table(...))

# ✅ ПРАВИЛЬНО — функция принимает tuple
content_3 = render_tbl1_kt(parse_md_table(...))
```

### Всегда добавляй оба класса `tbl` + вариант-специфичный

```python
out.append(f"<table class='tbl {table_class}'>")  # ✅
# НЕ: out.append(f"<table class='{table_class}'>")  # ❌ CSS-правила table.tbl td НЕ применятся
```

### Защищай _filter_columns от IndexError

```python
for i in col_indices:
    if i < len(row):
        new_row.append(row[i])
    else:
        new_row.append("")  # защита от IndexError
```

### Не хардкодь «нет данных на стадии Пресейл»

```python
# ❌ НЕПРАВИЛЬНО — заглушка для Пресейл
for n in range(1, 6):
    out.append(f"<td class='col-result'>— нет данных (Пресейл) —</td>")

# ✅ ПРАВИЛЬНО — читаем из MD
sec4_text = extract_section(REPORT_MD, 4)
# парсим и рендерим
```

## Шаг 10: проверка готового отчёта

После сборки проверь:

```python
# 1. CSS содержит все правила
assert "border: 1px solid #d1cfd7" in html  # сетка
assert "#fee2e2 !important" in html           # подкраска critical
assert "#fef3c7 !important" in html           # подкраска warning
assert ".report-indicator {" in html          # синий фон индикатора

# 2. HTML имеет правильные классы
assert "class='tbl tbl-kt'" in html          # оба класса
assert "report-indicator-circle" in html     # индикатор

# 3. Подкраска применена
import re
trs = re.findall(r"<tr[^>]*status-critical[^>]*>", html)
assert len(trs) > 0  # хотя бы одна critical строка

# 4. Preview-логика работает (pitfall #27)
previews = re.findall(r'<span class="tbl-preview">([^<]+)</span>', html)
for p in previews:
    assert "Заполняется" not in p, f"❌ Preview показывает правило, не итог: {p}"
    assert "не пресейл" not in p.lower(), f"❌ Preview показывает правило: {p}"
```

## Шаг 11: hardcoded-скрипт и его ограничение

На 2026-08-06 `scripts/build_html_report.py` **hardcoded** на проект 504-595:

```python
REPORT_MD = Path("/tmp/project_504-595_report.md").read_text(encoding="utf-8")
```

Для других проектов сейчас создаются **копии скрипта**:
- `cp scripts/build_html_report.py /tmp/build_html_<code>.py`
- Заменить hardcoded путь на нужный
- Запустить

**TODO (не реализовано 2026-08-06):** переделать на generic с CLI:
```bash
python3 scripts/build_html_report.py --code 504-595
python3 scripts/build_html_report.py --code 503-152
```

## Чек-лист восстановления после поломки CSS

1. Сравни `/tmp/report_<timestamp>.html` (эталон) с текущим
2. Сделай `diff` старого CSS и текущего
4. Ключевые слова для поиска потерянного:
   - `border: 1px solid #d1cfd7` (сетка)
   - `#fee2e2` + `!important` (подкраска critical)
   - `#fef3c7` + `!important` (подкраска warning)
   - `.variant-tbl[open]` (стиль открытой таблицы)
   - `.report-indicator { background: #2563eb }` (синий фон индикатора)
5. Если нашёл потерю — добавь обратно. Не пытайся «улучшить» — сначала восстанови.

## Резервные копии (эталоны) в профиле

`~/.hermes/profiles/fst-control/`:
- `build_html_report_ЭТАЛОН-V1.py` (533 строки, 18.6 КБ)
- `report_ЭТАЛОН-V1.css` (4.2 КБ)
- `report_ЭТАЛОН-V1.html` (4.2 КБ)

Восстановление:
```bash
cp ~/.hermes/profiles/fst-control/*ЭТАЛОН-V1.* templates/
cp ~/.hermes/profiles/fst-control/build_html_report_ЭТАЛОН-V1.py scripts/
```

**Не** удалять эталонные файлы пока сборщик не стал generic (--code).
