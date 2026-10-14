# Процедура: WORD Форма 1 из MD-отчёта

**Создано:** 2026-08-07 (live-probe).

---

## TL;DR

```bash
# 1. Сгенерировать MD
python3 scripts/build_html_report.py --code 504-595

# 2. Сгенерировать WORD
python3 scripts/build_word_report.py --code 504-595

# 3. Открыть /tmp/project_504-595_report_WORD-форма1.docx в Word
```

## Что это

**WORD Форма 1** — `.docx`-документ, структурно похожий на HTML-отчёт:

| HTML | WORD Форма 1 |
|------|--------------|
| `<details>` (свёрнуты) | **Все таблицы раскрыты** |
| CSS `background-color` | **Заливка ячеек** через `w:shd` |
| Эмодзи 🔴🟡🟢 | **Текст + цвет фона** |
| Цвета в CSS | **Цвета в OOXML атрибутах** |

## Что НЕ переносимо (компенсация)

| HTML | WORD Форма 1 |
|------|--------------|
| Подсветка всей строки | **Заливка каждой ячейки** |
| `<details>` интерактивный | Подразделы в документе |
| Status preview в `<summary>` | **Статус-бокс** в начале раздела |
| Эмодзи в строке | **Текст** «Критическое» / «Существенное» / «Норма» |
| `<div class="report-indicator-circle">` | Текстовый «Общий вердикт: Болен» |

## Чистота — нет MD-артефактов

| Артефакт | Статус |
|----------|--------|
| `**жирный**` | ❌ Нет |
| `# заголовок` | ❌ Нет |
| `\| разделитель` | ❌ Нет |
| ` ```код блок` | ❌ Нет |
| `<html> теги` | ❌ Нет |
| `\`code\` инлайн` | ❌ Нет |
| Эмодзи | ❌ Нет |

## Архитектура

```
scripts/build_word_report.py
├── COLORS (палитра, выровнена с templates/report.css)
├── OOXML утилиты
│   ├── hex_to_rgb()
│   ├── set_cell_background() — через w:shd
│   ├── set_cell_border() — через w:tcBorders
│   ├── set_cell_text() — run.font.bold, color_rgb, size
│   ├── add_table_with_header() — заливка строк через _color
│   ├── add_paragraph() — параграф с align/space
│   ├── add_heading() — заголовок 3-х уровней
│   ├── add_status_box() — статус-бокс (Болен/Здоров/...)
│   ├── add_paragraph_md() — убирает ** и `code`
│   └── add_horizontal_line() — граница снизу параграфа
├── build_word_report_from_data(data) → Document
│   Рисует: разделы 3-8, иконку вердикта, статус-боксы
├── parse_md_to_data(md_path) → dict
│   Парсит MD, fallback по разделам если verdict/итог пуст
├── _parse_section() — парсит таблицы 5-9 столбцов
├── _color_for_text() — вычисляет _color из текста
└── main() — CLI
    ├── --code <code> — путь к MD по умолчанию
    ├── --md <path> — custom MD path
    ├── --output <path> — custom .docx path
    └── --data-json <path> — JSON с готовыми данными
```

## Цветовая палитра

```python
COLORS = {
    "critical_bg": "FEE2E2", "critical_text": "991B1B",  # Критическое
    "warning_bg": "FEF3C7",  "warning_text": "92400E",  # Существенное
    "info_bg": "DBEAFE",     "info_text": "1E40AF",     # Информационное
    "healthy_bg": "DCFCE7",  "healthy_text": "166534",  # Норма / Здоров
    "neutral_bg": "F3F4F6",  "neutral_text": "4B5563",  # Неопределено
    "ref_bg": "F9FAFB",      "ref_text": "6B7280",      # Справочно
    "header_bg": "1E40AF",   "header_text": "FFFFFF",   # Заголовок
}
```

## Pitfall #59: ключ в COLORS — `f"{row_color}_bg"`, НЕ `row_color`

```python
# ❌ Неправильно (как было в первый раз):
if row_color and row_color in COLORS:  # row_color='critical', в COLORS нет 'critical'
    bg = COLORS[f"{row_color}_bg"]
    # bg = None

# ✅ Правильно:
if row_color and f"{row_color}_bg" in COLORS:  # 'critical_bg' есть
    bg = COLORS[f"{row_color}_bg"]
    # bg = "FEE2E2"
```

## Pitfall #60: order matters — fallback ПОСЛЕ парсинга секций

```python
# ❌ Неправильно (как было в первый раз):
def parse_md_to_data(md_path):
    # Парсим verdict
    # FALLBACK: строим summary_sections из data["section_3"]  # ← но они ещё пустые!
    # Парсим секции
    ...

# ✅ Правильно:
def parse_md_to_data(md_path):
    # Парсим verdict
    # Парсим секции
    # FALLBACK: строим summary_sections из data["section_3"]  # ← теперь они есть
    ...
```

## Pitfall #61: set_cell_background должен удалять старый shd

При повторном вызове `set_cell_background` на одной ячейке — добавляется **второй** `w:shd`, что ломает отображение. Решение:

```python
def set_cell_background(cell, color_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    # Удаляем существующие shd (если есть)
    for shd in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(shd)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)
```

## Pitfall #62: set_cell_border — то же самое

```python
def set_cell_border(cell, color_hex="D1D5DB", size=4):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    # Удаляем старые
    for old in tcPr.findall(qn("w:tcBorders")):
        tcPr.remove(old)
    # Создаём новые
    tcBorders = OxmlElement("w:tcBorders")
    ...
```

## Pitfall #63: WD_ORIENT, не WD_ORIENTATION

```python
# ❌ Неправильно:
from docx.enum.section import WD_ORIENTATION
section.orientation = WD_ORIENTATION.LANDSCAPE  # NameError

# ✅ Правильно:
from docx.enum.section import WD_ORIENT
section.orientation = WD_ORIENT.LANDSCAPE
```

## Автоматизация

Если нужно генерировать WORD для всех проектов в /tmp/:

```bash
#!/bin/bash
for md in /tmp/project_*_report.md; do
    code=$(echo "$md" | sed 's/.*project_\(.*\)_report\.md/\1/')
    if [ "$md" != "/tmp/project_${code}_report.md" ]; then continue; fi
    python3 scripts/build_word_report.py --code "$code"
done
```

## Интеграция с /tmp/run_<code>_rebuild.py

После пересборки MD вызывать:

```bash
python3 scripts/build_word_report.py --code "$code"
```

## Поддержка

| Аспект | Поддержка |
|--------|-----------|
| Word 365 | ✅ полная |
| Word 2019+ | ✅ полная |
| LibreOffice 7+ | ✅ полная |
| Word 2016 | ⚠️ открывает, но может потерять заливку |
| Word 2010 | ⚠️ открывает, но `w:shd` может игнориться |
| Google Docs | ⚠️ конвертирует, но теряет подсветку |

## ProTips

1. **Для печати**: раздел 7 с «Текущая дата формирования» — обновляется при следующей генерации.
2. **Для архива**: после пересборки отчёта — делать `.docx` снапшот с датой.
3. **Для рассылки**: отправлять только тот проект, который нужен — не весь.
4. **Для сравнения**: можно извлечь `data-dict` через `parse_md_to_data()` и сравнивать между проектами.

## Связанные артефакты

| Файл | Назначение |
|------|-----------|
| `scripts/build_word_report.py` | Генератор |
| `references/word-report-procedure.md` | Эта инструкция |
| `~/Вопросы по MCP 2026_08_07 v2.md` | Архив вопросов к разработчикам |
| `templates/report.css` | Эталон цветов (HTML) |
| `scripts/build_html_report.py` | HTML-генератор (для сравнения) |
| `scripts/get_effort.py` | Трудозатраты (для данных v0.3+) |
| `scripts/get_project_budget.py` | Финансы (для данных v0.3+) |
| `scripts/get_metamodel.py` | Титул/CoreVersion (для данных v0.3+) |
