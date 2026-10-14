__version__ = "1.0.19"
"""
build_word_report.py — Генератор WORD Форма 1 для fst-project-health.

Создаёт .docx-документ на основе MD-отчёта (project_<code>_report.md).
Все таблицы раскрыты. Цвет строк через заливку ячеек (w:shd).
Без MD-артефактов (**, #, |, ```, <html>) — чистый Word-документ.

Использование:
    python3 scripts/build_word_report.py --code 504-595
    python3 scripts/build_word_report.py --code 504-595 \\
        --md /tmp/project_504-595_report.md \\
        --output /tmp/project_504-595_report_WORD-форма1.docx

Создано: 2026-08-07, live-probe.
Требования: python-docx >= 1.0.0.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

Использует 4 уровня данных из MD:
1. Раздел 3 — таблица 9 столбцов (Код, Наименование, План, Прогноз, Факт, ...)
2. Раздел 4 — таблица 5 столбцов (Показатель, Результат, Детализация, Статус)
3. Раздел 5 — таблица 9 столбцов (Код, Название, План, Прогноз, Факт, Просрочка)
4. Раздел 6 — таблица 3 столбца (Показатель, Результат)
5. Раздел 7 — таблица 3 столбца (Показатель, Значение)

ЦВЕТОВАЯ СХЕМА (выровнена с HTML templates/report.css):
- critical  → FEE2E2 (фон) / 991B1B (текст) — Критическое
- warning   → FEF3C7 (фон) / 92400E (текст) — Существенное
- info      → DBEAFE (фон) / 1E40AF (текст) — Информационное
- healthy   → DCFCE7 (фон) / 166534 (текст) — Норма / Здоров
- neutral   → F3F4F6 (фон) / 4B5563 (текст) — Неопределено
- ref       → F9FAFB (фон) / 6B7280 (текст) — Справочно
- header    → 1E40AF (фон) / FFFFFF (текст) — Заголовок
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ═══════════════════════════════════════════════════════════════════════════════
# ЦВЕТОВАЯ ПАЛИТРА
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    # Критические (красный)
    "critical_bg": "FEE2E2",
    "critical_text": "991B1B",
    # Существенные (жёлтый)
    "warning_bg": "FEF3C7",
    "warning_text": "92400E",
    # Информационные (синий)
    "info_bg": "DBEAFE",
    "info_text": "1E40AF",
    # Норма (зелёный)
    "healthy_bg": "DCFCE7",
    "healthy_text": "166534",
    # Неопределено (серый)
    "neutral_bg": "F3F4F6",
    "neutral_text": "4B5563",
    # Справочно (нейтральный)
    "ref_bg": "F9FAFB",
    "ref_text": "6B7280",
    # Заголовок
    "header_bg": "1E40AF",
    "header_text": "FFFFFF",
}


# ═══════════════════════════════════════════════════════════════════════════════
# УТИЛИТЫ ДЛЯ OOXML
# ═══════════════════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_color: str) -> RGBColor:
    """Преобразует hex-color (6 chars, без #) в RGBColor."""
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def set_cell_background(cell, color_hex: str):
    """Задаёт цвет фона ячейки через w:shd."""
    tc_pr = cell._tc.get_or_add_tcPr()
    # Удаляем существующий shd (если есть)
    for shd in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(shd)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def set_cell_border(cell, color_hex: str = "D1D5DB", size: int = 4):
    """Добавляет границы ячейки через w:tcBorders."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    # Удаляем существующий tcBorders
    for old in tcPr.findall(qn("w:tcBorders")):
        tcPr.remove(old)
    tcBorders = OxmlElement("w:tcBorders")
    for border_name in ["top", "left", "bottom", "right"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(size))
        border.set(qn("w:color"), color_hex)
        tcBorders.append(border)
    tcPr.append(tcBorders)


def set_cell_text(cell, text: str, bold: bool = False, color_hex: str = "000000",
                  size: int = 10, align: str = "left"):
    """Заполняет ячейку текстом."""
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = hex_to_rgb(color_hex)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_table_with_header(doc, headers: list[str], rows: list[dict]):
    """Создаёт таблицу с заголовками и подсветкой строк.

    Args:
        doc: Document.
        headers: список заголовков столбцов.
        rows: список dict-строк данных. Ключ "_color" задаёт цвет строки.
    """
    n_cols = len(headers)
    n_rows = len(rows) + 1
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Заголовки
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_text(cell, header, bold=True, color_hex=COLORS["header_text"], size=10, align="center")
        set_cell_background(cell, COLORS["header_bg"])
        set_cell_border(cell, COLORS["header_bg"], size=6)

    # Строки
    for r_idx, row_dict in enumerate(rows, start=1):
        row = table.rows[r_idx]
        row_color = row_dict.get("_color", None)
        # ⚠️ Pitfall: ключ в COLORS — f"{row_color}_bg", НЕ row_color
        if row_color and f"{row_color}_bg" in COLORS:
            bg = COLORS[f"{row_color}_bg"]
            text_color = COLORS[f"{row_color}_text"]
        else:
            bg = None
            text_color = "000000"

        for c_idx, header in enumerate(headers):
            cell = row.cells[c_idx]
            value = row_dict.get(header, "")
            if value is None:
                value = ""
            value = str(value)
            align = row_dict.get(f"_align_{header}", "left")
            set_cell_text(cell, value, bold=False, color_hex=text_color, size=9, align=align)
            if bg:
                set_cell_background(cell, bg)
            set_cell_border(cell)


def add_paragraph(doc, text: str, bold: bool = False, size: int = 11, color: str = "000000",
                  align: str = "left", space_after: int = 6):
    """Добавляет параграф."""
    p = doc.add_paragraph()
    p.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = hex_to_rgb(color)
    return p


def add_heading(doc, text: str, level: int = 1):
    """Добавляет заголовок."""
    sizes = {1: 18, 2: 14, 3: 12}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.font.size = Pt(sizes.get(level, 11))
    run.font.bold = True
    if level == 1:
        run.font.color.rgb = hex_to_rgb(COLORS["header_bg"])
    else:
        run.font.color.rgb = hex_to_rgb("1F2937")


def add_status_box(doc, status: str, color: str = "warning"):
    """Добавляет выделенный блок статуса."""
    bg = COLORS.get(f"{color}_bg", "F3F4F6")
    text_color = COLORS.get(f"{color}_text", "000000")
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    set_cell_text(cell, f"Статус: {status}", bold=True, color_hex=text_color, size=12, align="center")
    set_cell_background(cell, bg)
    set_cell_border(cell, bg, size=8)


def add_paragraph_md(doc, md_text: str):
    """Парсит MD-параграф (убирает ** и `code`)."""
    md_text = md_text.replace("**", "")
    md_text = re.sub(r"`([^`]+)`", r"\1", md_text)
    md_text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", md_text)
    add_paragraph(doc, md_text)


def add_horizontal_line(doc):
    """Добавляет горизонтальную линию."""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D1D5DB")
    pBdr.append(bottom)
    pPr.append(pBdr)


# ═══════════════════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ ОТЧЁТА
# ═══════════════════════════════════════════════════════════════════════════════

def build_word_report_from_data(data: dict) -> Document:
    """Строит WORD-документ из data-словаря.

    Структура data:
    {
        "project_code": "504-595",
        "project_id": 4595,
        "project_name": "Космодром Жуковский внедрение ИСУП",
        "verdict": "Болен",
        "verdict_color": "critical",
        "summary_sections": [
            {"#": 1, "цвет": "Жёлтый", "раздел": "3. Сроки", "статус": "Требует внимания", "детали": "2 КТ", "_color": "warning"},
            ...
        ],
        "section_3": {
            "статус": "Требует внимания",
            "итог": "2 критических, 1 существенное, 0 информационных",
            "color": "warning",
            "rows": [
                {"#": "1", "Цвет": "Красный", "Статус": "Критическое", "Код": "104-719", ...},
                ...
            ]
        },
        "section_4": {
            "статус": "Здоров",
            "color": "healthy",
            "rows": [...],
            "details_4": {"rows": [...], "method": "..."},
            "details_5": {"rows": [...]}
        },
        "section_5": {...},
        "section_6": {...},
        "section_7": {...},
        "summary_counts": [
            {"#": "1", "Тип": "Критическое", "Р.3": "2", "Р.4": "0", "Р.5": "3", "Р.6": "3", "Итого": "8", "_color": "critical"},
            ...
        ]
    }
    """
    doc = Document()

    # Landscape A4
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    # === ЗАГОЛОВОК ===
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Отчёт о здоровье проекта")
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = hex_to_rgb(COLORS["header_bg"])

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(f"«{data.get('project_name', 'Проект')}»")
    run.font.size = Pt(16)
    run.font.italic = True
    run.font.color.rgb = hex_to_rgb("1F2937")

    add_paragraph(doc, "", space_after=4)

    # === Метаданные ===
    # v1.0.19: нумерация 3-9 (вместо старой 3-7).
    # Источник отчёта: "живой" (по MCP сейчас) или "слепок" (по MD из MCP).
    generator = data.get("generator", "")
    snapshot_ts = data.get("snapshot_timestamp", "") or ""
    if generator == "fst-project-health" or generator == "":
        # Живой отчёт — нет слепка.
        source_label = "MCP (в реальном времени)"
    elif snapshot_ts:
        source_label = f"Слепок от {snapshot_ts}"
    else:
        source_label = "Слепок из MCP (timestamp не указан)"
    meta_rows = [
        ("Target", f"{data.get('project_code', '?')} (ProjectId={data.get('project_id', '?')})"),
        ("Дата формирования", datetime.now().strftime("%Y-%m-%d %H:%M") + " (локальное время)"),
        ("Источник", source_label),
        ("MCP", "PMForesight MCP v3.2.4"),
        ("Scope", "полный отчёт по проекту (разделы 3-9)"),
        ("Версия", "WORD Форма 1 — все таблицы раскрыты, с подсветкой строк"),
    ]
    table = doc.add_table(rows=len(meta_rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(meta_rows):
        c0 = table.rows[i].cells[0]
        c1 = table.rows[i].cells[1]
        set_cell_text(c0, k, bold=True, color_hex="1F2937", size=10)
        set_cell_text(c1, v, bold=False, color_hex="1F2937", size=10)
        set_cell_background(c0, COLORS["ref_bg"])
        set_cell_border(c0)
        set_cell_border(c1)

    add_paragraph(doc, "")

    # === ОБЩИЙ ВЕРДИКТ ===
    add_heading(doc, "Общий вердикт", level=1)
    verdict = data.get("verdict", "Неопределено")
    verdict_color = data.get("verdict_color", "neutral")
    add_status_box(doc, verdict, color=verdict_color)

    add_paragraph_md(doc, f"Правило: {data.get('verdict_reason', 'автоопределение из разделов 3-6')}.")

    add_paragraph(doc, "Сводка по содержательным разделам:", bold=True, size=11, space_after=4)
    if data.get("summary_sections"):
        add_table_with_header(doc, ["#", "Цвет", "Раздел", "Статус", "Детали"], data["summary_sections"])

    # === РАЗДЕЛ 3 ===
    sec3 = data.get("section_3", {})
    if sec3:
        add_heading(doc, "3. Оценка здоровья проекта с точки зрения сроков", level=1)
        add_paragraph_md(doc, f"Итог по замечаниям: {sec3.get('итог', '?')}.")
        add_status_box(doc, sec3.get("статус", "Неопределено"), color=sec3.get("color", "neutral"))
        if sec3.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Цвет", "Статус", "Код", "Наименование", "План", "Прогноз", "Факт", "Исполнитель"],
                sec3["rows"],
            )
        if sec3.get("сводка"):
            add_paragraph_md(doc, sec3["сводка"])
        if sec3.get("метод"):
            add_paragraph_md(doc, sec3["метод"])

    # === РАЗДЕЛ 4 ===
    sec4 = data.get("section_4", {})
    if sec4:
        add_heading(doc, "4. Проверка полноты заполнения проекта", level=1)
        add_paragraph_md(doc, f"Итог по замечаниям: {sec4.get('итог', '0 критических, 0 существенных, 0 информационных, 0 «Неопределено»')}.")
        add_status_box(doc, sec4.get("статус", "Неопределено"), color=sec4.get("color", "healthy"))
        if sec4.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Цвет", "Статус", "Показатель", "Результат", "Детализация"],
                sec4["rows"],
            )
        if sec4.get("сводка"):
            add_paragraph_md(doc, sec4["сводка"])

        # 4.1 Трудозатраты
        details_4 = sec4.get("details_4")
        if details_4:
            add_heading(doc, "4.1 Детали по показателю 4 — Трудозатраты", level=2)
            if details_4.get("источник"):
                add_paragraph_md(doc, f"Источник: {details_4['источник']}.")
            if details_4.get("описание"):
                add_paragraph_md(doc, details_4["описание"])
            if details_4.get("rows"):
                add_table_with_header(
                    doc,
                    ["#", "Цвет", "Пользователь", "Специализация", "Plan (ч)", "Forecast (ч)", "Fact (ч)", "Строк", "Статус"],
                    details_4["rows"],
                )
            if details_4.get("сводка"):
                add_paragraph_md(doc, details_4["сводка"])

        # 4.2 Финансы
        details_5 = sec4.get("details_5")
        if details_5:
            add_heading(doc, "4.2 Детали по показателю 5 — Финансы", level=2)
            if details_5.get("источник"):
                add_paragraph_md(doc, f"Источник: {details_5['источник']}.")
            if details_5.get("описание"):
                add_paragraph_md(doc, details_5["описание"])
            if details_5.get("rows"):
                add_table_with_header(
                    doc,
                    ["#", "Цвет", "Что", "Сумма", "Статус"],
                    details_5["rows"],
                )

    # === РАЗДЕЛ 5 ===
    sec5 = data.get("section_5", {})
    if sec5:
        add_heading(doc, "5. Актуальность прогнозов по проекту", level=1)
        add_paragraph_md(doc, f"Итог по замечаниям: {sec5.get('итог', '?')}.")
        add_status_box(doc, sec5.get("статус", "Неопределено"), color=sec5.get("color", "neutral"))
        if sec5.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Цвет", "Статус", "Код", "Название", "План", "Прогноз", "Факт", "Дней просрочки"],
                sec5["rows"],
            )
        if sec5.get("сводка"):
            add_paragraph_md(doc, sec5["сводка"])

    # === РАЗДЕЛ 6: ПОКАЗАТЕЛИ ПРОЕКТА (v1.0.19 — 16 показателей) ===
    sec6 = data.get("section_6", {})
    if sec6:
        add_heading(doc, "6. Показатели проекта (16 индикаторов)", level=1)
        add_paragraph_md(doc, f"Итог по замечаниям: {sec6.get('итог', '?')}.")
        # Главная таблица: 4 колонки (#, Показатель, Результат, Детали)
        if sec6.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Показатель", "Результат", "Детали"],
                sec6["rows"],
            )
        # Вложенные таблицы (### 6.N в MD) — каждый показатель отдельно.
        indicators = sec6.get("indicators") or []
        for ind in indicators:
            num = ind.get("number", "")
            name = ind.get("name", "")
            title = ind.get("table_title", "")
            table = ind.get("table", []) or []
            if not table:
                continue
            # Заголовок 6.N
            add_heading(doc, f"6.{num} {name}", level=2)
            if title:
                add_paragraph_md(doc, f"*{title}*")
            # Колонки для вложенной таблицы (определяем по первой строке).
            if table:
                hdr = list(table[0].keys())
                # Отфильтруем служебные ключи (начинающиеся с _).
                hdr = [k for k in hdr if not k.startswith("_")]
                rows_for_docx = [{k: r.get(k, "") for k in hdr} for r in table]
                # Добавляем цветовое кодирование severity (если есть).
                for i, r in enumerate(rows_for_docx):
                    sev = table[i].get("_severity", "normal")
                    color = {
                        "critical": "critical",
                        "substantial": "warning",
                        "informational": "ref",
                        "normal": "healthy",
                    }.get(sev, "neutral")
                    r["_color"] = color
                add_table_with_header(doc, hdr, rows_for_docx)

    # === РАЗДЕЛ 7: ФИНАНСОВЫЙ СТАТУС (v1.0.19 — был 6) ===
    sec7 = data.get("section_7", {})
    if sec7:
        add_heading(doc, "7. Финансовый статус проекта", level=1)
        add_paragraph_md(doc, f"Итог по замечаниям: {sec7.get('итог', '?')}.")
        add_status_box(doc, sec7.get("статус", "Неопределено"), color=sec7.get("color", "neutral"))
        if sec7.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Показатель", "Результат", "Детализация"],
                sec7["rows"],
            )
        if sec7.get("сводка"):
            add_paragraph_md(doc, sec7["сводка"])

    # === РАЗДЕЛ 8: ТЕХНИЧЕСКИЕ ДАННЫЕ (v1.0.19 — был 7) ===
    sec8 = data.get("section_8", {})
    if sec8:
        add_heading(doc, "8. Технические данные отчёта", level=1)
        add_status_box(doc, sec8.get("статус", "Информация"), color=sec8.get("color", "neutral"))
        if sec8.get("rows"):
            add_table_with_header(
                doc,
                ["#", "Показатель", "Значение"],
                sec8["rows"],
            )

    # === РАЗДЕЛ 9: ИНДИКАТОР (v1.0.19 — общий вердикт) ===
    sec9 = data.get("section_9", {})
    if sec9:
        add_heading(doc, "9. Индикатор (общий вердикт)", level=1)
        add_status_box(doc, sec9.get("статус", "Неопределено"), color=sec9.get("color", "neutral"))
        if sec9.get("rows"):
            # Определяем фактическое число колонок по первой строке.
            first_row = sec9["rows"][0]
            actual_cols = max(len(first_row), len(KNOWN_HEADERS.get(len(first_row), [])))
            headers = KNOWN_HEADERS.get(actual_cols, list(first_row.keys()))
            # Если реальных столбцов меньше — рендерим без служебных.
            headers = [h for h in headers if h in first_row]
            add_table_with_header(doc, headers, sec9["rows"])
        if sec9.get("сводка"):
            add_paragraph_md(doc, sec9["сводка"])

    # === СВОДКА (общий итог) ===
    add_heading(doc, "Сводка по отчёту в целом", level=1)
    add_paragraph_md(doc, f"Вердикт: {verdict}.")

    # Новая нумерация (v1.0.19): summary_text содержит текст из раздела «Сводка по отчёту».
    if data.get("summary_text"):
        # Извлекаем содержимое раздела (без заголовка).
        st = data["summary_text"]
        # Убираем первую строку (заголовок).
        lines = st.split("\n", 1)
        body = lines[1] if len(lines) > 1 else st
        # Рендерим как markdown (с поддержкой списков и жирного).
        for line in body.strip().split("\n"):
            if line.strip():
                add_paragraph_md(doc, line)
    # Legacy: старая нумерация с pipe-таблицей.
    elif data.get("summary_counts"):
        add_paragraph_md(doc, "Сводка по замечаниям по разделам:")
        # Новая нумерация: 8 колонок (Р.3 ... Р.9)
        add_table_with_header(
            doc,
            ["#", "Тип", "Р.3", "Р.4", "Р.5", "Р.6", "Р.7", "Р.8", "Р.9", "Итого"],
            data["summary_counts"],
        )

    # Главные проблемы
    if data.get("проблемы"):
        add_heading(doc, "Главные проблемы проекта", level=2)
        for p in data["проблемы"]:
            add_paragraph_md(doc, p)

    if data.get("плюсы"):
        add_heading(doc, "Положительные моменты", level=2)
        for p in data["плюсы"]:
            add_paragraph_md(doc, p)

    # Футер
    add_paragraph(doc, "")
    add_horizontal_line(doc)
    add_paragraph_md(doc, "Конец отчёта (WORD Форма 1). Сгенерировано скиллом fst-project-health.")

    return doc


def parse_md_to_data(md_path: Path) -> dict:
    """Парсит MD-отчёт в data-словарь для build_word_report_from_data.

    Использует регуляные выражения для извлечения:
    - Заголовка, метаданных, общего вердикта
    - Таблиц разделов 3-7 (по каждой таблице определяет столбцы и цвет строк)

    Цвет строк определяется по наличию ключевых слов в 3-м столбце:
    - «Критическое» / «Просрочен» → critical
    - «Существенное» → warning
    - «Норма» / «Здоров» / «Актуально» → healthy
    - «Справочно» / «Информация» → ref
    - «Неопределено» → neutral
    """
    src = md_path.read_text(encoding="utf-8")

    # v1.0.19: парсим YAML front-matter (generator, snapshot_timestamp).
    generator = ""
    snapshot_ts = ""
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", src, re.DOTALL)
    if fm_match:
        fm_body = fm_match.group(1)
        m_gen = re.search(r"^generator:\s*['\"]?([^'\"\n]+)['\"]?", fm_body, re.MULTILINE)
        if m_gen:
            generator = m_gen.group(1).strip()
        m_ts = re.search(r"^snapshot_timestamp:\s*['\"]?([^'\"\n]+)['\"]?", fm_body, re.MULTILINE)
        if m_ts:
            snapshot_ts = m_ts.group(1).strip()

    data = {
        "project_code": "",
        "project_id": 0,
        "project_name": "",
        "verdict": "Неопределено",
        "verdict_color": "neutral",
        "verdict_reason": "",
        "generator": generator,
        "snapshot_timestamp": snapshot_ts,
        "summary_sections": [],
        "section_3": {},
        "section_4": {},
        "section_5": {},
        "section_6": {},
        "section_7": {},
        "section_8": {},
        "section_9": {},
        "summary_counts": [],
        "проблемы": [],
        "плюсы": [],
    }

    # Target / ProjectId
    m = re.search(r"\*\*Target:\*\*\s*([^\s()]+)\s*\(ProjectId=(\d+)\)", src)
    if m:
        data["project_code"] = m.group(1)
        data["project_id"] = int(m.group(2))

    # Project name
    m = re.search(r"# Отчёт о здоровье проекта «([^»]+)»", src)
    if m:
        data["project_name"] = m.group(1)

    # Split into sections
    sections = re.split(r"\n## ", src)

    # Main header — verdict + summary_sections (с fallback)
    # v1.0.19: в новой нумерации шапка `# Отчёт о здоровье проекта ...`
    # НЕ содержит `**Статус:**`. Вердикт перенесён в раздел 9 «Индикатор
    # (общий вердикт)», ищем там.
    verdict_text = ""
    for grp in sections:
        # Шапка отчёта (для project_name и обратной совместимости со старым MD)
        if grp.startswith("# Отчёт"):
            m = re.search(r"\*\*Статус:\*\*\s*(.+)", grp)
            if m:
                verdict_text = m.group(1).strip()
        # Новая нумерация: раздел 9 «Индикатор (общий вердикт)»
        if grp.startswith("9. ") and "Индикатор" in grp:
            m = re.search(r"\*\*Статус:\s*([^*\n]+?)\*?\*", grp)
            if m:
                verdict_text = m.group(1).strip()
            # Убрать эмодзи, если есть
            verdict_text = re.sub(r"[🀀-🿿]", "", verdict_text).strip()
            # Классифицируем
            if "Болен" in verdict_text or "БОЛЕН" in verdict_text:
                data["verdict"] = "Болен"
                data["verdict_color"] = "critical"
            elif "Требует внимания" in verdict_text:
                data["verdict"] = "Требует внимания"
                data["verdict_color"] = "warning"
            elif "Здоров" in verdict_text:
                data["verdict"] = "Здоров"
                data["verdict_color"] = "healthy"
            m_rule = re.search(r"\*\*Правило:\*\*\s*(.+)", grp)
            if m_rule:
                data["verdict_reason"] = m_rule.group(1).strip()
            break

    # Если нашли verdict выше — записать
    if verdict_text and data["verdict"] == "Неопределено":
        data["verdict"] = verdict_text
        if "Болен" in verdict_text:
            data["verdict_color"] = "critical"
        elif "Требует внимания" in verdict_text:
            data["verdict_color"] = "warning"
        elif "Здоров" in verdict_text:
            data["verdict_color"] = "healthy"

    # Summary table из «общего вердикта» (раздел 9) или из шапки (старый MD)
    summary_data = None
    for grp in sections:
        if grp.startswith("# Отчёт"):
            # Старый формат: summary в шапке (после verbatim-разделителя ---)
            sm = self_extract_table(grp, 5, flexible=True)
            if sm and len(sm[0]) >= 5:
                summary_data = sm
                break
        if grp.startswith("9. ") and "Индикатор" in grp:
            # Новая нумерация: summary внутри раздела 9
            sm = self_extract_table(grp, 7, flexible=True)
            if sm:
                summary_data = sm
                break
    if summary_data:
        for row in summary_data[:8]:
            if len(row) >= 2 and row[0]:
                # Старый формат: row = [#, Цвет, Раздел, Статус, Детали]
                # Новый формат: row = [#, Раздел, Название, Статус, ...]
                # Унифицированное извлечение:
                idx = 0
                n_str = row[idx].strip() if idx < len(row) else ""
                if not n_str:
                    continue
                if len(row) >= 5:
                    # Старый: [#, Цвет, Раздел, Статус, Детали]
                    color_text = row[1]
                    name = row[2]
                    status = row[3]
                else:
                    # Новый: [#, Раздел, Название, Статус(?, или в др. кол)]
                    color_text = row[-2] if len(row) >= 4 else ""
                    name = row[1] if len(row) >= 2 else ""
                    status = row[-1] if len(row) >= 3 else ""
                data["summary_sections"].append({
                    "#": n_str,
                    "Цвет": color_text,
                    "Раздел": name,
                    "Статус": status,
                    "Детали": "",
                    "_color": _color_for_text(color_text + " " + status),
                })
    # legacy: если ничего не нашли, но в старом MD есть шапка verbatim
    if not data["summary_sections"]:
        for grp in sections:
            if grp.startswith("# Отчёт"):
                m = re.search(r"\*\*Правило:\*\*\s*(.+)", grp)
                if m:
                    data["verdict_reason"] = m.group(1).strip()
                sm = self_extract_table(grp, 5, flexible=True)
                if sm:
                    for row in sm[:6]:
                        if len(row) >= 5 and row[0]:
                            data["summary_sections"].append({
                                "#": row[0],
                                "Цвет": row[1],
                                "Раздел": row[2],
                                "Статус": row[3],
                                "Детали": row[4],
                                "_color": _color_for_text(row[1] + " " + row[3]),
                            })
                break

    # Section parsers
    # v1.0.19: гибкий подбор раздела. Поскольку в новом MD:
    #   - раздел 6 = «Показатели проекта» (16 шт, 4 кол),
    #   - раздел 7 = «Финансы» (4 кол),
    #   - раздел 8 = «Тех. данные» (без таблицы),
    #   - раздел 9 = «Индикатор (сводка)»,
    # — а в старом MD: 6 = Финансы, 7 = Тех.данные, 8 = Сводка.
    # Парсим ВСЕ подходящие pipe-таблицы гибким парсером и считаем,
    # какие подходят по семантике (по заголовку и числу колонок).
    for sec in sections:
        sec_head = sec.split("\n", 1)[0].strip()
        # Игнорировать первую секцию — это front-matter (yaml) или шапка
        if sec_head.startswith("---") or sec_head.startswith("# Отчёт"):
            continue
        # 3. Замечания по срокам
        if sec_head.startswith("3. ") and "срокам" in sec_head.lower():
            data["section_3"] = _parse_section(sec, expected_cols=9)
        # 4. Полнота заполнения
        elif sec_head.startswith("4. ") and "полнота" in sec_head.lower():
            data["section_4"] = _parse_section(sec, expected_cols=5)
        # 5. Актуальность прогнозов
        elif sec_head.startswith("5. ") and "прогноз" in sec_head.lower():
            data["section_5"] = _parse_section(sec, expected_cols=9)
        # 6. Показатели проекта (новый формат ИЛИ Финансы (старый))
        elif sec_head.startswith("6. "):
            if "показател" in sec_head.lower() or "indicators" in sec_head.lower():
                # Новая нумерация: показатели. Записываем в section_6 для DOCX,
                # парсер сам разберётся с числом колонок через flexible=True.
                data["section_6"] = _parse_section(sec, expected_cols=4)
                # v1.0.19: парсим вложенные таблицы показателей (### 6.N).
                data["section_6"]["indicators"] = _parse_indicators_from_md(sec)
            else:
                # Старая нумерация: Финансы
                data["section_6"] = _parse_section(sec, expected_cols=3)
        # 7. Финансы (новый) или Тех.данные (старый)
        elif sec_head.startswith("7. "):
            # В новой нумерации это Финансы. В старой — Тех.данные.
            # flexible=True в _parse_section разберётся.
            data["section_7"] = _parse_section(sec, expected_cols=4)
        # 8. (новый) Тех.данные — таблица с 3 колонками (#, Показатель, Значение)
        elif sec_head.startswith("8. "):
            # В новой нумерации — Тех. данные.
            if "тех" in sec_head.lower() or "technical" in sec_head.lower():
                data["section_8"] = _parse_section(sec, expected_cols=3)
        # 9. (новый) Индикатор (сводка-индикатор) — вердикт + таблица по 6 разделам.
        elif sec_head.startswith("9. ") and ("индикатор" in sec_head.lower() or "indicator" in sec_head.lower()):
            # Парсим как обычный раздел: статус из "**Статус: ..." + таблица.
            data["section_9"] = _parse_section(sec, expected_cols=3)
        # "## Сводка по отчёту" (новая нумерация) — текстовая сводка без номера.
        elif sec_head.startswith("Сводка по отчёту") or sec_head.startswith("Сводка по отчету"):
            # Парсим вердикт, главные проблемы и т.д. — текстовый раздел.
            data["summary_text"] = sec
        # Старая нумерация: 8. (сводка)
        elif sec_head.startswith("8. ") and "замечани" in sec_head.lower():
            # Legacy summary_counts (только старые MD)
            summary = self_extract_table(sec, 7, flexible=False)
            if summary:
                for row in summary[:6]:
                    if len(row) >= 7 and row[0]:
                        data["summary_counts"].append({
                            "#": row[0],
                            "Тип": row[1],
                            "Р.3": row[2] or "0",
                            "Р.4": row[3] or "0",
                            "Р.5": row[4] or "0",
                            "Р.6": row[5] or "0",
                            "Итого": row[6] or "0",
                            "_color": _color_for_text(row[1]),
                        })

    # FALLBACK: если summary_sections пуст, строим из разделов 3-6
    # (этот блок ПОСЛЕ парсинга секций, чтобы fallback работал)
    if not data["summary_sections"]:
        section_map = [
            ("3", "3. Оценка сроков", data["section_3"]),
            ("4", "4. Полнота заполнения", data["section_4"]),
            ("5", "5. Актуальность прогнозов", data["section_5"]),
            ("6", "6. Финансовый статус", data["section_6"]),
        ]
        for n, name, sec in section_map:
            if not sec:
                continue
            status = sec.get("status", "Неопределено")
            color = sec.get("color", "neutral")
            color_word = {"critical": "Красный", "warning": "Жёлтый", "healthy": "Зелёный",
                          "ref": "Нейтральный", "neutral": "Серый"}.get(color, "Серый")
            detail = sec.get("итог", "Нет данных")
            data["summary_sections"].append({
                "#": n,
                "Цвет": f"{color_word} ({status})",
                "Раздел": name,
                "Статус": status,
                "Детали": detail,
                "_color": color,
            })

    # FALLBACK: если verdict не получен, вычисляем
    if data["verdict"] == "Неопределено" and data["summary_sections"]:
        prio = {"critical": 3, "warning": 2, "ref": 1, "neutral": 0, "healthy": 0}
        max_color = max(data["summary_sections"],
                        key=lambda x: prio.get(x["_color"], 0))
        color = max_color["_color"]
        status = max_color["Статус"]
        if color == "critical":
            data["verdict"] = "Болен"
            data["verdict_color"] = "critical"
        elif color == "warning":
            data["verdict"] = "Требует внимания"
            data["verdict_color"] = "warning"
        else:
            data["verdict"] = "Здоров"
            data["verdict_color"] = "healthy"
        data["verdict_reason"] = f"вычислено из {max_color['Раздел']} ({status})"

    return data


def self_extract_table(text: str, expected_cols: int, flexible: bool = False) -> list:
    """Извлекает первую таблицу с ожидаемым количеством столбцов.

    v1.0.19 (для совместимости с перенумерацией разделов в fst-project-health):
    если `flexible=True`, при отсутствии таблицы с ровно `expected_cols`
    возвращает первую попавшуюся pipe-таблицу (любое число колонок).
    Это нужно потому, что разделы могут теперь иметь разное число
    столбцов:
      - Раздел 5 (прогнозы): 8 кол (раньше было 9 — без «Факт»).
      - Раздел 6 (показатели): 4 кол + вложенные 3-кол.
      - Раздел 7 (финансы): 4 кол.
    """
    # Попытка 1: строгое число колонок
    for line in text.split("\n"):
        if line.startswith("|") and line.count("|") >= expected_cols:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) == expected_cols:
                lines = text.split("\n")
                idx = lines.index(line)
                rows = []
                cur_idx = idx + 2  # skip separator
                while cur_idx < len(lines):
                    l = lines[cur_idx]
                    if not l.startswith("|"):
                        break
                    cells = [c.strip() for c in l.split("|")[1:-1]]
                    if len(cells) == expected_cols:
                        rows.append(cells)
                    cur_idx += 1
                if rows:
                    return rows

    # Попытка 2 (flexible): первая попавшаяся pipe-таблица
    if flexible:
        for line in text.split("\n"):
            if line.startswith("|") and "|" in line[1:]:
                # Пропустить строку-разделитель (|---|---|...)
                if re.match(r"^\|[\s\-:|]+\|\s*$", line):
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 2:
                    lines = text.split("\n")
                    idx = lines.index(line)
                    # Следующая строка должна быть разделитель
                    sep_idx = idx + 1
                    if sep_idx < len(lines) and re.match(r"^\|[\s\-:|]+\|\s*$", lines[sep_idx]):
                        rows = []
                        cur_idx = sep_idx + 1
                        actual_cols = len(cells)
                        while cur_idx < len(lines):
                            l = lines[cur_idx]
                            if not l.startswith("|"):
                                break
                            row_cells = [c.strip() for c in l.split("|")[1:-1]]
                            if len(row_cells) == actual_cols:
                                rows.append(row_cells)
                            cur_idx += 1
                        if rows:
                            return rows
    return []


def _color_for_text(text: str) -> str:
    """Возвращает цвет по тексту."""
    text_lower = text.lower()
    if "критическ" in text_lower or "просрочен" in text_lower or "красный" in text_lower:
        return "critical"
    if "существенн" in text_lower or "жёлт" in text_lower or "информационн" in text_lower:
        return "warning"
    if "здоров" in text_lower or "норма" in text_lower or "актуально" in text_lower or "зелён" in text_lower:
        return "healthy"
    if "справочно" in text_lower or "нейтральный" in text_lower:
        return "ref"
    if "неопредел" in text_lower:
        return "neutral"
    return "neutral"


def _parse_indicators_from_md(sec_text: str) -> list:
    """Парсит 16 показателей из раздела 6 MD.

    Возвращает список dict-ов:
        {"number": "1", "name": "...", "table_title": "...",
         "table": [{"col1": ..., "_severity": "normal"}, ...]}

    Severity извлекается из HTML-комментария в последней ячейке каждой
    строки: <!-- 6.N severity="critical|substantial|informational|normal" -->
    """
    indicators = []
    sec_lines = sec_text.split("\n")
    i = 0
    # Найдём подзаголовки "### 6.N"
    while i < len(sec_lines):
        m = re.match(r"^### 6\.(\d+)\s+(.+)$", sec_lines[i])
        if not m:
            i += 1
            continue
        sub_num = m.group(1)
        sub_name = m.group(2).strip()
        i += 1

        # Заголовок таблицы (опционально) — строка вида *Что-то*
        table_title = ""
        if i < len(sec_lines) and sec_lines[i].startswith("*"):
            table_title = sec_lines[i].strip("*").strip()
            i += 1

        # Пустая строка
        if i < len(sec_lines) and sec_lines[i].strip() == "":
            i += 1

        # Header pipe-table
        if i >= len(sec_lines) or not sec_lines[i].startswith("|"):
            continue
        hdr_cells = [c.strip() for c in sec_lines[i].split("|")[1:-1]]
        i += 1
        # Divider
        if i < len(sec_lines) and re.match(r"^\|[\s\-:|]+\|\s*$", sec_lines[i]):
            i += 1

        # Rows
        rows = []
        while i < len(sec_lines):
            line = sec_lines[i]
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) < 2:
                i += 1
                continue
            last_cell = cells[-1]
            m_s = re.search(r'<!--\s*6\.\d+\s+severity="([^"]+)"\s*-->', last_cell)
            severity = m_s.group(1) if m_s else "normal"
            if m_s:
                cells[-1] = re.sub(r'\s*<!--\s*6\.\d+\s+severity="[^"]+"\s*-->\s*', '', last_cell).strip()
            row = dict(zip(hdr_cells, cells))
            row["_severity"] = severity
            rows.append(row)
            i += 1

        if rows:
            indicators.append({
                "number": sub_num,
                "name": sub_name,
                "table_title": table_title,
                "table": rows,
            })

    return indicators


def _parse_section(sec_text: str, expected_cols: int) -> dict:
    """Парсит раздел 3-7."""
    header = sec_text.split("\n")[0]
    section = {
        "title": header,
        "status": "Неопределено",
        "color": "neutral",
        "итог": "",
        "rows": [],
    }

    # Status
    m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", sec_text)
    if m:
        section["status"] = m.group(1).strip()
    # Итог
    m = re.search(r"\*\*Итог по замечаниям:\*\*\s*(.+)", sec_text)
    if m:
        section["итог"] = m.group(1).strip()

    # Color based on status
    if "Болен" in section["status"]:
        section["color"] = "critical"
    elif "Требует внимания" in section["status"]:
        section["color"] = "warning"
    elif "Здоров" in section["status"]:
        section["color"] = "healthy"
    elif "Справочно" in section["status"] or "Информация" in section["status"]:
        section["color"] = "ref"

    # Main table (v1.0.19: динамическое число колонок).
    # Передаём expected_cols, но если строго не нашли — flexible=True
    # (см. self_extract_table).
    rows = self_extract_table(sec_text, expected_cols, flexible=True)
    # Фактическое число колонок = max по найденным строкам
    actual_cols = expected_cols
    if rows:
        actual_cols = max(len(r) for r in rows)
    for row in rows:
        if len(row) < actual_cols:
            continue
        record = {}
        headers = KNOWN_HEADERS.get(actual_cols, KNOWN_HEADERS.get(expected_cols, []))
        for i, header_word in enumerate(headers):
            if i < len(row):
                record[header_word] = row[i]
        # Color — на основе статуса в строке
        record["_color"] = _color_for_text(" ".join(row[1:5]))
        section["rows"].append(record)

    return section


# Маппинг header → столбцы
# v1.0.19: расширен для перенумерованных разделов fst-project-health.
# В MD теперь разделы имеют разное число столбцов:
#   3 (Сроки) — 9 кол (раньше) или 8 кол (новый формат, нет «Факт»)
#   4 (Полнота) — 5 кол (без «Цвет»)
#   5 (Прогнозы) — 9 кол (раньше) или 8 кол (новый)
#   6 (Показатели) — 4 кол (# | Показатель | Результат | Детали)
#   7 (Финансы) — 4 кол (# | Показатель | Результат | Детализация)
#   8 (Тех. данные) — без таблицы, только 6 строк
KNOWN_HEADERS = {
    # Раздел 3 — 8 или 9 столбцов
    9: ["#", "Цвет", "Статус", "Код", "Наименование", "План", "Прогноз", "Факт", "Исполнитель"],
    8: ["#", "Цвет", "Статус", "Код", "Наименование", "План", "Прогноз", "Дней", "Исполнитель"],
    # Раздел 4 — 5 столбцов (без столбца "Цвет")
    5: ["#", "Показатель", "Результат", "Детализация", "Статус"],
    # Раздел 5 — 8 или 9 (см. выше)
    # Раздел 6 (Показатели проекта) — 4 столбца
    # Раздел 7 (Финансы) — 4 столбца (та же структура, но «Детализация»).
    # Унифицируем: один entry для 4-кол.
    4: ["#", "Показатель", "Результат", "Детализация"],
    # Раздел 8 (Тех. данные) — 3 столбца
    3: ["#", "Показатель", "Значение"],
    # Сводка замечаний — 7 столбцов (старый формат)
    7: ["#", "Тип", "Р.3", "Р.4", "Р.5", "Р.6", "Итого"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Генератор WORD Форма 1 для fst-project-health"
    )
    parser.add_argument("--code", type=str, help="Код проекта (например, 504-595)")
    parser.add_argument("--md", type=str, help="Путь к MD-отчёту (по умолчанию ищется /tmp/project_<code>_report.md)")
    parser.add_argument("--output", type=str, help="Путь к .docx-файлу (по умолчанию /tmp/project_<code>_report_WORD-форма1.docx)")
    parser.add_argument("--data-json", type=str, help="JSON с готовыми данными (data-словарь)")
    args = parser.parse_args()

    if not (args.code or args.md or args.data_json):
        parser.print_help()
        return 1

    # Загружаем данные
    if args.data_json:
        import json
        data = json.loads(Path(args.data_json).read_text(encoding="utf-8"))
    else:
        md_path = Path(args.md) if args.md else Path(f"/tmp/project_{args.code}_report.md")
        if not md_path.exists():
            print(f"❌ MD не найден: {md_path}")
            return 1
        print(f"📖 Парсим MD: {md_path}")
        data = parse_md_to_data(md_path)

    print(f"📊 Данные: {data.get('project_code', '?')} — {data.get('verdict', '?')}")
    print(f"   Раздел 3: {len(data.get('section_3', {}).get('rows', []))} строк")
    print(f"   Раздел 4: {len(data.get('section_4', {}).get('rows', []))} строк")
    print(f"   Раздел 5: {len(data.get('section_5', {}).get('rows', []))} строк")
    print(f"   Раздел 6: {len(data.get('section_6', {}).get('rows', []))} строк")
    print(f"   Раздел 7: {len(data.get('section_7', {}).get('rows', []))} строк")

    # Строим документ
    doc = build_word_report_from_data(data)

    # Сохраняем
    if args.output:
        output_path = Path(args.output)
    elif args.code:
        output_path = Path(f"/tmp/project_{args.code}_report_WORD-форма1.docx")
    else:
        output_path = Path("/tmp/project_report_WORD-форма1.docx")

    doc.save(output_path)
    print(f"\n✅ WORD-отчёт сохранён: {output_path} ({output_path.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
