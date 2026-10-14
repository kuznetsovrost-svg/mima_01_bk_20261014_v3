"""
build_html_report.py v2 — генератор HTML с таблицами-открывашками для проекта 504-595.

Правила:
- Реальные данные из /tmp/project_504-595_report.md (разделы 3-7)
- Подкраска строк по статусу (critical/warning/none)
- <details>/<summary> сдвигает контент ниже (НЕ абсолютное позиционирование)
- Минимальный CSS — адаптивный, читается на любом экране
"""
import re
import json
from pathlib import Path
from datetime import datetime

REPORT_MD = Path("/tmp/project_504-595_report.md").read_text(encoding="utf-8")
PROJECT_JSON = json.loads(Path("/tmp/proj_504-595.json").read_text(encoding="utf-8"))
SECTION_4_DATA = json.loads(Path("/tmp/section_4_data.json").read_text(encoding="utf-8"))

PROJECT_CODE = PROJECT_JSON.get("Code", "504-595")
PROJECT_NAME = (PROJECT_JSON.get("Name") or "").strip()
PROJECT_ID = PROJECT_JSON.get("ProjectId", 4595)
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============ Парсер MD-таблиц ============
def parse_md_table(text):
    """Ищет первую таблицу в тексте, возвращает (headers, rows)."""
    lines = text.split("\n")
    table_lines = []
    in_table = False
    for line in lines:
        if line.startswith("|"):
            table_lines.append(line)
            in_table = True
        elif in_table and line.strip():
            # Таблица кончилась
            break
    if not table_lines:
        return [], []
    headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
    # Пропускаем разделитель (|---|---|...)
    body_rows = []
    for line in table_lines[2:]:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        body_rows.append(cells)
    return headers, body_rows


def extract_section(text, section_num):
    """Извлекает раздел section_num (3..7) из MD-отчёта."""
    pattern = rf"## {section_num}\. .*?(?=## \d|## Сводка)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else ""


def _extract_preview(section_md: str) -> str:
    """Извлекает «Статус раздела:» и «Итог по замечаниям:» (или «Итог:») из MD-раздела
    для preview-bar.

    Возвращает объединённую строку вида:
      'Требует внимания — 2 критических КТ, 1 существенное КТ'
      'Здоров — без замечаний'
      'Болен — все 3 показателя = «Да» (критические)'
      'Болен — 69 критических, 14 существенных, 0 информационных'

    Формат: «Статус раздела» + (если есть) « — Итог».

    Если статус не найден — возвращает «Нет данных».
    """
    status = ""
    summary = ""

    m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", section_md)
    if m:
        status = m.group(1).strip()

    # Итог по замечаниям: (стандартный) или Итог: (например, в финансах)
    m = re.search(r"\*\*(?:Итог по замечаниям|Итог):\*\*\s*(.+)", section_md)
    if m:
        summary = m.group(1).strip()

    # Если «Итог» нет в MD — вычисляем из таблицы показателей
    if not summary:
        summary = _auto_summary(section_md)

    if status and summary:
        return f"{status} — {summary}"
    elif status:
        return status
    elif summary:
        return summary
    return "Нет данных"


def _auto_summary(section_md: str) -> str:
    """Вычисляет итог по замечаниям из таблицы показателей (если «Итог» в MD нет).

    Считает сколько показателей «Да» (критично) и «Неопределено» в колонке «Результат».
    """
    n_critical = 0  # «Да» — считаем критическими
    n_uncertain = 0  # «Неопределено»
    for line in section_md.split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue
        # cells[0]=#, cells[1]=Показатель, cells[2]=Результат
        if cells[2] == "Да":
            n_critical += 1
        elif cells[2] == "Неопределено":
            n_uncertain += 1

    parts = []
    if n_critical:
        parts.append(f"{n_critical} показателей = «Да»")
    if n_uncertain:
        parts.append(f"{n_uncertain} «Неопределено»")
    if not parts:
        return "без замечаний"
    return ", ".join(parts)


# ============ Статус → CSS-класс ============
def status_class(status_text):
    """Определяет CSS-класс по статусу из MD."""
    s = status_text.lower()
    if "критическ" in s or "красн" in s or "🔴" in status_text:
        return "status-critical"
    if "существен" in s or "жёлт" in s or "🟡" in status_text:
        return "status-warning"
    if "информацион" in s or "⚪" in status_text or "норма" in s:
        return "status-info"
    return ""


# ============ Генерация таблиц ============
def render_tbl1_kt(table):
    """tbl1: замечания по срокам (5 колонок).

    Принимает tuple (headers, rows) от parse_md_table.
    MD-структура: [#, Цвет, Статус, Код, Наименование, План, Прогноз, Факт, Исполнитель]
    FIGMA:        [#, Код, Наименование, План, Прогноз]
    """
    headers, rows = table
    out = []
    out.append("<table class='tbl tbl-kt'>")
    out.append("<thead><tr><th>#</th><th>Код</th><th>Наименование</th><th>План</th><th>Прогноз</th></tr></thead><tbody>")
    for r in rows:
        # Защита от коротких строк
        color_text = r[1] if len(r) > 1 else ""    # 🔴 Красный / 🟡 Жёлтый
        cls = status_class(color_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td>{r[0] if len(r) > 0 else ''}</td>")    # #
        out.append(f"<td>{r[3] if len(r) > 3 else ''}</td>")    # Код
        out.append(f"<td>{r[4] if len(r) > 4 else ''}</td>")    # Наименование
        out.append(f"<td>{r[5] if len(r) > 5 else ''}</td>")    # План
        out.append(f"<td>{r[6] if len(r) > 6 else ''}</td>")    # Прогноз
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl2_completeness():
    """tbl2: полнота заполнения (5 строк показателей).

    ⚠️ ВАЖНО: данные должны заполняться **на любой стадии ЖЦ**, включая Пресейл.
    Пять показателей:
      1. Куратор назначен      → {r[N].owner}
      2. РП назначен           → {r[N].leader}
      3. Паспорт на стадии Инициирование → {r[N].passport}
      4. Актуальность трудозатрат      → {r[N].effort}
      5. График платежей               → {r[N].paygraph}

    Стадия ЖЦ влияет только на **интерпретацию** (pitfall #16):
    - На «Пресейл» паспорт/трудозатраты/платежи могут быть пустыми — это НОРМА.
    - На «Инициирование» и позже — это ЗАМЕЧАНИЯ.
    """
    rows_data = [
        (1, "Куратор назначен", SECTION_4_DATA["p1"]["result"], SECTION_4_DATA["p1"]["detail"]),
        (2, "РП назначен", SECTION_4_DATA["p2"]["result"], SECTION_4_DATA["p2"]["detail"]),
        (3, "Паспорт готов на стадии Инициирование", SECTION_4_DATA["p3"]["result"], SECTION_4_DATA["p3"]["detail"]),
        (4, "Актуальность данных проекта по трудозатратам", SECTION_4_DATA["p4"]["result"], SECTION_4_DATA["p4"]["detail"]),
        (5, "Корректность заполнения графика платежей проекта", SECTION_4_DATA["p5"]["result"], SECTION_4_DATA["p5"]["detail"]),
    ]
    out = []
    out.append("<table class='tbl tbl-completeness'>")
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Результат</th></tr></thead><tbody>")
    for n, name, result, detail in rows_data:
        # В tbl2 НЕТ подкраски (только индикаторы «Да/Нет/Неопределено» в result-detail строке)
        cls = status_class(result) if "Нет" in result else ""
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td class='col-num'>{n}</td>")
        out.append(f"<td class='col-name'>{name}</td>")
        out.append(f"<td class='col-result'>{detail}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl3_overdue():
    """tbl3: актуальность прогнозов.

    MD-структура: [#, Цвет, Код КТ, Название, План, Прогноз, Факт, Дней просрочки, Статус, Исполнитель]
    FIGMA:        [#, Код, Название, План, Прогноз, Просрочка дн]
    """
    sec5_text = extract_section(REPORT_MD, 5)
    headers, rows = parse_md_table(sec5_text)
    out = []
    out.append("<table class='tbl tbl-overdue'>")
    out.append("<thead><tr><th>#</th><th>Код</th><th>Название</th><th>План</th><th>Прогноз</th><th>Просрочка, дн</th></tr></thead><tbody>")
    for r in rows:
        color_text = r[1] if len(r) > 1 else ""    # 🔴 Красный / 🟡 Жёлтый
        cls = status_class(color_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td>{r[0]}</td>")   # #
        out.append(f"<td>{r[2]}</td>")   # Код КТ
        out.append(f"<td>{r[3]}</td>")   # Название
        out.append(f"<td>{r[4]}</td>")   # План
        out.append(f"<td>{r[5]}</td>")   # Прогноз
        out.append(f"<td>{r[7]}</td>")   # Дней просрочки
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl4_finance():
    """tbl4: финансы (3 показателя × 70px строки)."""
    sec6_text = extract_section(REPORT_MD, 6)
    headers, rows = parse_md_table(sec6_text)
    out = []
    out.append("<table class='tbl tbl-finance'>")
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Результат</th></tr></thead><tbody>")
    for r in rows:
        # r = [#, Показатель, Результат, Детализация]
        # FIGMA: nmb, name (показатель), result (с детализацией)
        # Берём детализацию для определения статуса (там есть "критическое замечание")
        detail_text = r[3] if len(r) > 3 else ""
        cls = status_class(detail_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td class='col-num'>{r[0]}</td>")
        out.append(f"<td class='col-name'>{r[1]}</td>")
        # Склеиваем result + детализацию для полноты
        full = f"{r[2]}. {r[3]}" if len(r) > 3 else r[2]
        out.append(f"<td class='col-result'>{full}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl5_tech():
    """tbl5: технические данные (6 показателей).

    ⚠️ ВАЖНО: данные должны заполняться **на любой стадии ЖЦ**, включая Пресейл.
    Это справочная информация о пользователе, MCP-сервере и версиях — она всегда
    доступна, независимо от того, на какой стадии находится проект.
    """
    sec7_text = extract_section(REPORT_MD, 7)
    rows_data = []
    for line in sec7_text.split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", line)
        if m and m.group(1).isdigit():
            rows_data.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    out = []
    out.append("<table class='tbl tbl-tech'>")
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Значение</th></tr></thead><tbody>")
    for n, name, value in rows_data:
        out.append("<tr>")
        out.append(f"<td class='col-num'>{n}</td>")
        out.append(f"<td class='col-name'>{name}</td>")
        out.append(f"<td class='col-value'>{value}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


# ============ Главный HTML ============
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Open Sans', Arial, sans-serif;
    background: #dbeafe;
    color: #000;
    padding: 24px;
    line-height: 1.5;
}

.report-container {
    max-width: 920px;
    margin: 0 auto;
}

/* === HEADER === */
.report-header {
    display: grid;
    grid-template-columns: 1fr 158px;
    gap: 0;
    margin-bottom: 20px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
}
.report-header-text {
    background: #2563eb;
    color: #ffffff;
    padding: 18px 20px;
    min-height: 158px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 10px;
}
.report-header-prefix {
    font-size: 15px;
    font-weight: 700;
}
.report-header-title {
    font-size: 22px;
    font-weight: 700;
    color: #fffcfc;
}
.report-header-meta {
    font-size: 13px;
    font-weight: 400;
}
.report-header-meta b { font-weight: 700; }
.report-indicator {
    background: #2563eb;
    padding: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 158px;
}
.report-indicator-circle {
    background: #ffffff;
    width: 136px;
    height: 136px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 13px;
    font-weight: 700;
    color: #000;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
    line-height: 1.2;
}
.report-indicator-circle .verdict-emoji { font-size: 28px; margin-bottom: 4px; }

/* === TABLE-OF-CONTENTS / COLLAPSIBLES === */
.variant-tbl {
    background: #ffffff;
    margin-bottom: 8px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.variant-tbl > summary {
    background: #d1cfd7;
    padding: 8px 14px;
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 700;
    list-style: none;
    transition: background .15s;
}
.variant-tbl > summary:hover { background: #c8c5cd; }
.variant-tbl > summary::-webkit-details-marker { display: none; }
.variant-tbl > summary::after {
    content: "▼";
    font-size: 10px;
    transition: transform .15s;
}
.variant-tbl[open] > summary::after { transform: rotate(180deg); }

.tbl-name { font-weight: 700; }
.tbl-preview { font-weight: 400; opacity: .8; font-size: 12px; }

.tbl-content {
    background: #ffffff;
    padding: 12px 16px;
    border-top: 1px solid #d1cfd7;
    overflow-x: auto;
}

/* === TABLE STYLES === */
table.tbl {
    border-collapse: collapse;
    width: 100%;
    font-size: 12px;
    color: #232326;
}
table.tbl th {
    background: #f7f7fa;
    text-align: left;
    padding: 6px 10px;
    border: 1px solid #d1cfd7;
    font-weight: 700;
    color: #374151;
    font-size: 12px;
}
table.tbl td {
    padding: 6px 10px;
    border: 1px solid #d1cfd7;
    vertical-align: middle;
}
table.tbl tr td.col-num {
    text-align: center;
    width: 40px;
    font-size: 11px;
}
table.tbl tr td.col-name {
    font-size: 11px;
    color: #232326;
}
table.tbl tr td.col-result,
table.tbl tr td.col-value {
    font-size: 11px;
    color: #232326;
}

/* === Row highlighting === */
table.tbl tr.status-critical td {
    background: #fee2e2 !important;
    font-weight: 700;
}
table.tbl tr.status-warning td {
    background: #fef3c7 !important;
}
table.tbl tr.status-info td {
    background: #f0fdf4 !important;
}

/* === Variant-specific styles === */
table.tbl-kt th,
table.tbl-kt td {
    height: 30px;
}
table.tbl-overdue th,
table.tbl-overdue td {
    height: 30px;
}
table.tbl-completeness th,
table.tbl-completeness td {
    height: 30px;
}
table.tbl-tech th,
table.tbl-tech td {
    height: 30px;
}
table.tbl-finance th {
    height: 30px;
}
table.tbl-finance td {
    height: 70px;
    vertical-align: top;
    padding-top: 10px;
}
table.tbl-finance td.col-name { font-weight: 700; }

/* === Footer === */
.report-footer {
    margin-top: 24px;
    padding: 12px;
    text-align: center;
    font-size: 11px;
    color: #475569;
}
</style>
"""

# Генерируем таблицы
content_3 = render_tbl1_kt(parse_md_table(extract_section(REPORT_MD, 3)))
content_4 = render_tbl2_completeness()
content_5 = render_tbl3_overdue()
content_6 = render_tbl4_finance()
content_7 = render_tbl5_tech()

# Preview-строки (берутся из MD-разделов — «Статус раздела:»)
preview_3 = _extract_preview(extract_section(REPORT_MD, 3))
preview_4 = _extract_preview(extract_section(REPORT_MD, 4))
preview_5 = _extract_preview(extract_section(REPORT_MD, 5))
preview_6 = _extract_preview(extract_section(REPORT_MD, 6))
preview_7 = "ℹ️ Нейтральный — справочная информация"

# Собираем HTML конкатенацией (CSS содержит { и }, ломает f-string)
HTML_BODY_HEAD = """
    <div class="report-header">
        <div class="report-header-text">
            <div class="report-header-prefix">Общая оценка здоровья проекта</div>
            <div class="report-header-title">__PROJECT_NAME__</div>
            <div class="report-header-meta"><b>Target:</b> __PROJECT_CODE__ (ProjectId=__PROJECT_ID__)</div>
            <div class="report-header-meta"><b>Отчёт создан:</b> __NOW__</div>
            <div class="report-header-meta"><b>MCP:</b> PMForesight v3.2.4</div>
        </div>
        <div class="report-indicator">
            <div class="report-indicator-circle">
                <div class="verdict-emoji">🔴</div>
                Проект болен
            </div>
        </div>
    </div>

    <details class="variant-tbl">
        <summary>
            <span class="tbl-name">Замечания по срокам:</span>
            <span class="tbl-preview">__PREVIEW_3__</span>
        </summary>
        <div class="tbl-content">
__CONTENT_3__
        </div>
    </details>

    <details class="variant-tbl">
        <summary>
            <span class="tbl-name">Полнота заполнения проекта:</span>
            <span class="tbl-preview">__PREVIEW_4__</span>
        </summary>
        <div class="tbl-content">
__CONTENT_4__
        </div>
    </details>

    <details class="variant-tbl">
        <summary>
            <span class="tbl-name">Актуальность прогнозов по проекту:</span>
            <span class="tbl-preview">__PREVIEW_5__</span>
        </summary>
        <div class="tbl-content">
__CONTENT_5__
        </div>
    </details>

    <details class="variant-tbl">
        <summary>
            <span class="tbl-name">Финансовый статус проекта:</span>
            <span class="tbl-preview">__PREVIEW_6__</span>
        </summary>
        <div class="tbl-content">
__CONTENT_6__
        </div>
    </details>

    <details class="variant-tbl">
        <summary>
            <span class="tbl-name">Технические данные отчёта:</span>
            <span class="tbl-preview">__PREVIEW_7__</span>
        </summary>
        <div class="tbl-content">
__CONTENT_7__
        </div>
    </details>

    <div class="report-footer">
        Сгенерировано скиллом <b>fst-project-health</b> · __PROJECT_CODE__ (ProjectId=__PROJECT_ID__) · MCP PMForesight v3.2.4
    </div>

</div>
</body>
</html>
"""

# Подстановка значений
body_html = (HTML_BODY_HEAD
    .replace("__PROJECT_NAME__", PROJECT_NAME)
    .replace("__PROJECT_CODE__", PROJECT_CODE)
    .replace("__PROJECT_ID__", str(PROJECT_ID))
    .replace("__NOW__", NOW)
    .replace("__PREVIEW_3__", preview_3)
    .replace("__PREVIEW_4__", preview_4)
    .replace("__PREVIEW_5__", preview_5)
    .replace("__PREVIEW_6__", preview_6)
    .replace("__PREVIEW_7__", preview_7)
    .replace("__CONTENT_3__", content_3)
    .replace("__CONTENT_4__", content_4)
    .replace("__CONTENT_5__", content_5)
    .replace("__CONTENT_6__", content_6)
    .replace("__CONTENT_7__", content_7)
)

HTML_HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт о здоровье проекта """ + PROJECT_CODE + """</title>
""" + CSS + """
</head>
<body>
<div class="report-container">
"""

HTML = HTML_HEAD + body_html

Path("/tmp/project_504-595_report.html").write_text(HTML, encoding="utf-8")
print(f"✅ HTML создан: /tmp/project_504-595_report.html")
print(f"   Размер: {len(HTML)} байт, {len(HTML.splitlines())} строк")
print()
print("Превью контента по разделам:")
print(f"  tbl1 (КТ): {content_3.count('<tr')} строк (включая header)")
print(f"  tbl2 (полнота): {content_4.count('<tr')} строк")
print(f"  tbl3 (прогнозы): {content_5.count('<tr')} строк")
print(f"  tbl4 (финансы): {content_6.count('<tr')} строк")
print(f"  tbl5 (тех. данные): {content_7.count('<tr')} строк")
print(f"  critical: {HTML.count('status-critical')}")
print(f"  warning:  {HTML.count('status-warning')}")
