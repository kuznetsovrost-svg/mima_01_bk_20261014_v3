"""
build_html_report.py — generic генератор HTML-отчёта для любого проекта.

Использование:
    python3 scripts/build_html_report.py --code 504-595
    python3 scripts/build_html_report.py --code 503-152 --output /tmp/custom.html
    python3 scripts/build_html_report.py --ls  # список доступных проектов

Ожидаемая структура в /tmp/:
    /tmp/project_<code>_report.md   # MD-отчёт (собирается scripts/rebuild_report.py)
    /tmp/proj_<code>.json           # метаданные проекта (собирается run_<code>_section_1.py)

Выход:
    /tmp/project_<code>_report.html — HTML-отчёт с:
      - цветным индикатором (radial-gradient, 4 статуса)
      - 5 таблицами-открывашками (KT, Полнота, Прогнозы, Финансы, Тех. данные)
      - подкраской строк по статусу (critical/warning/info)
      - preview-строками = «Статус раздела:» + « — Итог»

Импорт программный:
    from build_html_report import build_html
    html = build_html(report_md, project_data)
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


# ============ Парсер MD-таблиц ============
def parse_md_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Ищет первую pipe-table в тексте, возвращает (headers, rows)."""
    table_lines = []
    in_table = False
    for line in text.split("\n"):
        if line.startswith("|"):
            table_lines.append(line)
            in_table = True
        elif in_table and line.strip():
            break
    if not table_lines:
        return [], []
    headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
    body_rows = []
    for line in table_lines[2:]:  # пропускаем header + разделитель
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        body_rows.append(cells)
    return headers, body_rows


def extract_section(text: str, section_num: int) -> str:
    """Извлекает раздел section_num (3..7) из MD-отчёта."""
    pattern = rf"## {section_num}\. .*?(?=## \d|## Сводка)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else ""


# ============ Preview-строки ============
def _extract_preview(section_md: str) -> str:
    """Извлекает «Статус раздела:» и «Итог:» из MD-раздела для preview-bar.

    Формат: «Статус раздела» + (если есть) « — Итог».
    Если «Итог» нет в MD — вычисляем автоматически.
    """
    status = ""
    summary = ""

    m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", section_md)
    if m:
        status = m.group(1).strip()

    m = re.search(r"\*\*(?:Итог по замечаниям|Итог):\*\*\s*(.+)", section_md)
    if m:
        summary = m.group(1).strip()

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
    """Вычисляет итог по замечаниям из таблицы (если «Итог» в MD нет)."""
    n_critical = 0
    n_uncertain = 0
    for line in section_md.split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue
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
def status_class(status_text: str) -> str:
    s = status_text.lower()
    if "критическ" in s or "красн" in s or "🔴" in status_text:
        return "status-critical"
    if "существен" in s or "жёлт" in s or "🟡" in status_text:
        return "status-warning"
    if "информацион" in s or "⚪" in status_text or "норма" in s:
        return "status-info"
    return ""


# ============ Генерация таблиц ============
def render_tbl1_kt(report_md: str) -> str:
    """tbl1: замечания по срокам (5 колонок). MD-таблица раздела 3.
    Колонки MD: [#, Цвет, Статус, Код, Наименование, План, Прогноз, Факт, Исполнитель]
    Колонки FIGMA: [#, Код, Наименование, План, Прогноз]
    """
    headers, rows = parse_md_table(extract_section(report_md, 3))
    out = ["<table class='tbl tbl-kt'>"]
    out.append("<thead><tr><th>#</th><th>Код</th><th>Наименование</th><th>План</th><th>Прогноз</th></tr></thead><tbody>")
    for r in rows:
        color_text = r[1] if len(r) > 1 else ""
        cls = status_class(color_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td>{r[0] if len(r) > 0 else ''}</td>")
        out.append(f"<td>{r[3] if len(r) > 3 else ''}</td>")
        out.append(f"<td>{r[4] if len(r) > 4 else ''}</td>")
        out.append(f"<td>{r[5] if len(r) > 5 else ''}</td>")
        out.append(f"<td>{r[6] if len(r) > 6 else ''}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl2_completeness(report_md: str) -> str:
    """tbl2: полнота заполнения (5 показателей). Заполняется на ЛЮБОЙ стадии ЖЦ."""
    sec4_text = extract_section(report_md, 4)
    rows_data = []
    for line in sec4_text.split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", line)
        if m and m.group(1).isdigit():
            rows_data.append((int(m.group(1)), m.group(2).strip(),
                            m.group(3).strip(), m.group(4).strip(), m.group(5).strip()))
    out = ["<table class='tbl tbl-completeness'>"]
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Результат</th></tr></thead><tbody>")
    if not rows_data:
        for n, name in [(1, "Куратор назначен"), (2, "РП назначен"),
                        (3, "Паспорт готов на стадии Инициирование"),
                        (4, "Актуальность данных проекта по трудозатратам"),
                        (5, "Корректность заполнения графика платежей проекта")]:
            out.append(f"<tr><td class='col-num'>{n}</td>")
            out.append(f"<td class='col-name'>{name}</td>")
            out.append(f"<td class='col-result'>— нет данных —</td></tr>")
    for n, name, result, detail, status in rows_data:
        cls = ""
        if "Критическ" in status or "Нет" in result:
            cls = "status-critical"
        elif "Существен" in status or "Неопределено" in result:
            cls = "status-warning"
        full_result = f"{result} — {detail}" if detail else result
        out.append(f"<tr class='{cls}'>" if cls else "<tr>")
        out.append(f"<td class='col-num'>{n}</td>")
        out.append(f"<td class='col-name'>{name}</td>")
        out.append(f"<td class='col-result'>{full_result}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl3_overdue(report_md: str) -> str:
    """tbl3: актуальность прогнозов (6 колонок). MD-таблица раздела 5.
    Колонки MD: [#, Цвет, Код КТ, Название, План, Прогноз, Факт, Дней просрочки, Статус, Исполнитель]
    """
    headers, rows = parse_md_table(extract_section(report_md, 5))
    out = ["<table class='tbl tbl-overdue'>"]
    out.append("<thead><tr><th>#</th><th>Код</th><th>Название</th><th>План</th><th>Прогноз</th><th>Просрочка, дн</th></tr></thead><tbody>")
    for r in rows:
        color_text = r[1] if len(r) > 1 else ""
        cls = status_class(color_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td>{r[0] if len(r) > 0 else ''}</td>")
        out.append(f"<td>{r[2] if len(r) > 2 else ''}</td>")
        out.append(f"<td>{r[3] if len(r) > 3 else ''}</td>")
        out.append(f"<td>{r[4] if len(r) > 4 else ''}</td>")
        out.append(f"<td>{r[5] if len(r) > 5 else ''}</td>")
        out.append(f"<td>{r[7] if len(r) > 7 else ''}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl4_finance(report_md: str) -> str:
    """tbl4: финансы (3 показателя × 70px строки)."""
    headers, rows = parse_md_table(extract_section(report_md, 6))
    out = ["<table class='tbl tbl-finance'>"]
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Результат</th></tr></thead><tbody>")
    for r in rows:
        detail_text = r[3] if len(r) > 3 else ""
        cls = status_class(detail_text)
        out.append(f"<tr class='{cls}'>")
        out.append(f"<td class='col-num'>{r[0]}</td>")
        out.append(f"<td class='col-name'>{r[1]}</td>")
        full = f"{r[2]}. {r[3]}" if len(r) > 3 else r[2]
        out.append(f"<td class='col-result'>{full}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_tbl5_tech(report_md: str) -> str:
    """tbl5: тех. данные (6 показателей). Заполняется на ЛЮБОЙ стадии ЖЦ."""
    sec7_text = extract_section(report_md, 7)
    rows_data = []
    for line in sec7_text.split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", line)
        if m and m.group(1).isdigit():
            rows_data.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    out = ["<table class='tbl tbl-tech'>"]
    out.append("<thead><tr><th>#</th><th>Показатель</th><th>Значение</th></tr></thead><tbody>")
    if not rows_data:
        for n, name in [(1, "Пользователь"), (2, "Титул системы"),
                        (3, "URL MCP-сервера"), (4, "Версия скилла"),
                        (5, "Версия MCP"), (6, "Версия ПМ «Форсайт»")]:
            out.append(f"<tr><td class='col-num'>{n}</td>")
            out.append(f"<td class='col-name'>{name}</td>")
            out.append(f"<td class='col-value'>— нет данных —</td></tr>")
    for n, name, value in rows_data:
        out.append("<tr>")
        out.append(f"<td class='col-num'>{n}</td>")
        out.append(f"<td class='col-name'>{name}</td>")
        out.append(f"<td class='col-value'>{value}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


# ============ Сводный вердикт ============
def compute_verdict(report_md: str) -> tuple[str, str, str]:
    """Возвращает (text, status_class, emoji_unused) для индикатора.

    Логика:
      - Если ЛЮБОЙ из разделов 3/4/5/6 = Болен → status_class='sick', text='Проект болен'
      - Иначе если ЛЮБОЙ = Требует внимания → 'attention', 'Требует внимания'
      - Иначе → 'healthy', 'Здоров'
    """
    statuses = []
    for n in (3, 4, 5, 6):
        sec = extract_section(report_md, n)
        m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", sec)
        if m:
            statuses.append(m.group(1).strip())

    if any("Болен" in s or "БОЛЕН" in s for s in statuses):
        return ("Проект болен", "sick", "")
    if any("Требует внимания" in s for s in statuses):
        return ("Требует внимания", "attention", "")
    if any("Здоров" in s for s in statuses):
        return ("Здоров", "healthy", "")
    return ("Нет данных", "unknown", "")


# ============ Загрузка шаблона и CSS ============
def load_template(skill_dir: Path) -> tuple[str, str]:
    """Загружает templates/report.html и templates/report.css. Возвращает (html, css)."""
    html_path = skill_dir / "templates" / "report.html"
    css_path = skill_dir / "templates" / "report.css"
    if not html_path.exists():
        raise FileNotFoundError(f"Шаблон не найден: {html_path}")
    if not css_path.exists():
        raise FileNotFoundError(f"CSS не найден: {css_path}")
    html = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    return html, css


# ============ Главная функция ============
def build_html(report_md: str, project_data: dict, template_html: str = None,
               template_css: str = None) -> str:
    """Собирает финальный HTML.

    Args:
        report_md: содержимое /tmp/project_<code>_report.md
        project_data: dict с ключами Code, Name, ProjectId
        template_html: путь к templates/report.html (auto-detect если None)
        template_css: путь к templates/report.css (auto-detect если None)

    Returns:
        Полный HTML как строка.
    """
    project_code = project_data.get("Code", "???")
    project_name = (project_data.get("Name") or "").strip()
    project_id = project_data.get("ProjectId", 0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Render tables
    content_3 = render_tbl1_kt(report_md)
    content_4 = render_tbl2_completeness(report_md)
    content_5 = render_tbl3_overdue(report_md)
    content_6 = render_tbl4_finance(report_md)
    content_7 = render_tbl5_tech(report_md)

    # Preview-строки
    preview_3 = _extract_preview(extract_section(report_md, 3))
    preview_4 = _extract_preview(extract_section(report_md, 4))
    preview_5 = _extract_preview(extract_section(report_md, 5))
    preview_6 = _extract_preview(extract_section(report_md, 6))
    preview_7 = "ℹ️ Нейтральный — справочная информация"

    # Сводный вердикт
    verdict_text, verdict_status, _ = compute_verdict(report_md)

    # Load templates
    skill_dir = Path(__file__).parent.parent
    if template_html is None or template_css is None:
        html_tpl, css_tpl = load_template(skill_dir)
        if template_html is None:
            template_html = html_tpl
        if template_css is None:
            template_css = css_tpl

    # Делим HTML на «до content» и «после body», чтобы подставить CSS без экранирования
    # (CSS содержит { }, ломает f-string — используем replace)
    css_block = f"<style>\n{template_css}\n</style>"
    # Вставка CSS в <head>
    html_full = template_html.replace("</head>", css_block + "\n</head>")

    # Подстановка значений
    return html_full \
        .replace("{{ project_code }}", str(project_code)) \
        .replace("{{ project_name }}", project_name) \
        .replace("{{ project_id }}", str(project_id)) \
        .replace("{{ now }}", now) \
        .replace("{{ section_3_preview }}", preview_3) \
        .replace("{{ section_4_preview }}", preview_4) \
        .replace("{{ section_5_preview }}", preview_5) \
        .replace("{{ section_6_preview }}", preview_6) \
        .replace("{{ section_7_preview }}", preview_7) \
        .replace("{{ section_3_content }}", content_3) \
        .replace("{{ section_4_content }}", content_4) \
        .replace("{{ section_5_content }}", content_5) \
        .replace("{{ section_6_content }}", content_6) \
        .replace("{{ section_7_content }}", content_7) \
        .replace("{{ verdict_status }}", verdict_status) \
        .replace("{{ verdict_text }}", verdict_text)


# ============ Поиск проектов в /tmp ============
def list_available_projects() -> list[str]:
    """Возвращает список кодов проектов, для которых есть MD-отчёт."""
    codes = set()
    for md in Path("/tmp").glob("project_*_report.md"):
        m = re.search(r"project_([\w-]+)_report\.md", md.name)
        if m:
            codes.add(m.group(1))
    return sorted(codes)


def find_project_files(code: str) -> tuple[Path, Path]:
    """Находит пути к MD и JSON для кода. Бросает FileNotFoundError если нет."""
    md_path = Path(f"/tmp/project_{code}_report.md")
    json_path = Path(f"/tmp/proj_{code}.json")
    if not md_path.exists():
        available = list_available_projects()
        ctx = f"Доступные: {', '.join(available)}" if available else "В /tmp/ нет ни одного /tmp/project_*_report.md"
        raise FileNotFoundError(f"MD-отчёт не найден: {md_path}\n{ctx}")
    if not json_path.exists():
        raise FileNotFoundError(f"JSON-данные не найдены: {json_path}")
    return md_path, json_path


# ============ CLI ============
def main() -> Path:
    """CLI-обёртка: собирает /tmp/project_<code>_report.html.

    Использование:
        python3 scripts/build_html_report.py --code 504-595
        python3 scripts/build_html_report.py --ls  # список доступных
    """
    parser = argparse.ArgumentParser(
        description="Генератор HTML-отчёта для проекта fst-project-health."
    )
    parser.add_argument("--code", type=str, help="Код проекта (например, 504-595)")
    parser.add_argument("--output", type=str, help="Путь к выходному HTML (default: /tmp/project_<code>_report.html)")
    parser.add_argument("--ls", action="store_true", help="Список доступных проектов")
    args = parser.parse_args()

    if args.ls:
        codes = list_available_projects()
        if codes:
            print("Доступные проекты (есть /tmp/project_*_report.md):")
            for c in codes:
                print(f"  • {c}")
        else:
            print("В /tmp/ нет ни одного /tmp/project_*_report.md")
        return None

    if not args.code:
        parser.print_help()
        sys.exit(1)

    md_path, json_path = find_project_files(args.code)
    report_md = md_path.read_text(encoding="utf-8")
    project_data = json.loads(json_path.read_text(encoding="utf-8"))

    html = build_html(report_md, project_data)

    output = Path(args.output) if args.output else Path(f"/tmp/project_{args.code}_report.html")
    output.write_text(html, encoding="utf-8")

    # Сводка
    n_critical = html.count("status-critical")
    n_warning = html.count("status-warning")
    n_info = html.count("status-info")
    print(f"✅ HTML-отчёт собран: {output} ({len(html)} байт)")
    print(f"   status-critical: {n_critical}")
    print(f"   status-warning:  {n_warning}")
    print(f"   status-info:     {n_info}")
    return output


if __name__ == "__main__":
    main()
