#!/usr/bin/env python3
"""
json_to_html.py — генерация HTML-отчёта из JSON-слепка fst-project-health-snapshot.

НЕ вызывает fst-project-health (использует только данные из JSON-файла,
полученного из MCP). Не модифицирует другие скиллы.

Использование:
    python3 json_to_html.py --json outputs/504-595_2026-09-17_19-16-36.json
    python3 json_to_html.py --json path/to/snapshot.json --output my_report.html

Имя файла по умолчанию: <project_code>_<timestamp>_from_snapshot.html в текущей папке.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# AGPM-совместимая палитра (синхронизирована с fst-project-health/templates/report.css).
PALETTE = {
    "bg": "#f5f7fb",
    "paper": "#ffffff",
    "ink": "#101828",
    "muted": "#667085",
    "line": "#d9e0ea",
    "navy": "#071b3a",
    "hero_middle": "#09315c",
    "teal": "#075f6b",
    "gold": "#c89b3c",
    "hero_eyebrow": "#d7b76a",
    "table_head": "#0b2145",
    "good": "#0f7a5f",
    "mid": "#946200",
    "bad": "#b42318",
    "gray": "#64748b",
    "green_bg": "#dcfce7",
    "green_text": "#166534",
    "yellow_bg": "#fef3c7",
    "yellow_text": "#92400e",
    "red_bg": "#fee2e2",
    "red_text": "#991b1b",
    "gray_bg": "#f1f5f9",
    "gray_text": "#475569",
}

# Маппинг _color → CSS-фон.
COLOR_TO_BG = {
    "critical": PALETTE["red_bg"],
    "warning": PALETTE["yellow_bg"],
    "substantial": PALETTE["yellow_bg"],
    "informational": "#dbeafe",
    "normal": PALETTE["paper"],
    "healthy": PALETTE["green_bg"],
    "neutral": PALETTE["paper"],
}

# Маппинг verdict → цвет индикатора.
VERDICT_TO_GRADIENT = {
    "Болен": "radial-gradient(circle at center, #fca5a5 0%, #ef4444 60%, #dc2626 100%)",
    "Требует внимания": "radial-gradient(circle at center, #fde68a 0%, #f59e0b 60%, #d97706 100%)",
    "Здоров": "radial-gradient(circle at center, #86efac 0%, #22c55e 60%, #16a34a 100%)",
    "Неопределено": "radial-gradient(circle at center, #cbd5e1 0%, #9ca3af 60%, #6b7280 100%)",
}

VERDICT_TO_STATUS = {
    "Болен": "sick",
    "Требует внимания": "attention",
    "Здоров": "healthy",
    "Неопределено": "unknown",
}


def html_escape(s) -> str:
    if s is None:
        return ""
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_css() -> str:
    return f"""
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: 'Open Sans', Arial, sans-serif;
        background: {PALETTE['bg']};
        color: {PALETTE['ink']};
        padding: 24px;
        line-height: 1.5;
    }}
    .report-container {{ max-width: 920px; margin: 0 auto; }}
    .report-header {{
        display: grid;
        grid-template-columns: 1fr 172px;
        gap: 0;
        margin-bottom: 20px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 20px 44px rgba(16, 24, 40, 0.16);
        background: linear-gradient(135deg, {PALETTE['navy']} 0%, {PALETTE['hero_middle']} 56%, {PALETTE['teal']} 100%);
    }}
    .report-header-text {{
        color: #ffffff;
        padding: 18px 20px;
        min-height: 158px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        gap: 10px;
    }}
    .report-header-prefix {{
        font-size: 15px;
        font-weight: 700;
        color: {PALETTE['hero_eyebrow']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .report-header-title {{ font-size: 22px; font-weight: 700; color: #ffffff; }}
    .report-header-meta {{ font-size: 13px; color: rgba(255,255,255,0.82); }}
    .report-header-meta b {{ color: #ffffff; }}
    .report-indicator {{
        background: linear-gradient(135deg, {PALETTE['navy']} 0%, {PALETTE['hero_middle']} 56%, {PALETTE['teal']} 100%);
        padding: 6px;
        display: flex; align-items: center; justify-content: center;
        min-height: 172px;
    }}
    .report-indicator-circle {{
        width: 160px !important; height: 160px !important;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        text-align: center;
        font-size: 13px; font-weight: 700; color: #ffffff;
        text-shadow: 0 1px 3px rgba(0,0,0,0.6);
        text-transform: uppercase; letter-spacing: 0.5px;
        box-shadow: 0 6px 16px rgba(0,0,0,0.25), 0 2px 4px rgba(0,0,0,0.15);
    }}
    .section {{
        background: {PALETTE['paper']};
        border: 1px solid {PALETTE['line']};
        border-radius: 8px;
        margin-bottom: 12px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(16,24,40,0.06);
    }}
    .section summary {{
        background: #f8fafc;
        padding: 10px 16px;
        cursor: pointer;
        font-weight: 700;
        font-size: 14px;
        border-bottom: 1px solid {PALETTE['line']};
    }}
    .section[open] > summary {{ background: {PALETTE['gray_bg']}; }}
    .section-content {{ padding: 12px 16px; }}
    table.tbl {{
        border-collapse: collapse;
        width: 100%;
        font-size: 12px;
        color: {PALETTE['ink']};
    }}
    table.tbl th {{
        background: {PALETTE['table_head']};
        color: #ffffff;
        text-align: left;
        padding: 6px 10px;
        border: 1px solid {PALETTE['line']};
        font-weight: 700;
    }}
    table.tbl td {{
        padding: 6px 10px;
        border: 1px solid {PALETTE['line']};
        vertical-align: middle;
    }}
    .meta-box {{
        background: {PALETTE['gray_bg']};
        border-left: 4px solid {PALETTE['navy']};
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 12px;
        color: {PALETTE['muted']};
    }}
    .meta-box b {{ color: {PALETTE['ink']}; }}
    h2.section-title {{ font-size: 14px; margin: 0; }}
    """


def build_header(snap: dict) -> str:
    meta = snap.get("_meta", {})
    verdict = snap.get("verdict", "Неопределено")
    gradient = VERDICT_TO_GRADIENT.get(verdict, VERDICT_TO_GRADIENT["Неопределено"])
    project_name = snap.get("project_name", "")
    project_code = meta.get("project_code", "?")
    produced = meta.get("produced_at", "")
    generator = meta.get("generator", "?")

    return f"""
    <div class="report-header">
        <div class="report-header-text">
            <div class="report-header-prefix">📸 Слепок {html_escape(generator)}</div>
            <div class="report-header-title">{html_escape(project_code)}{(' — ' + html_escape(project_name)) if project_name else ''}</div>
            <div class="report-header-meta">
                <b>Verdict:</b> {html_escape(verdict)} &nbsp;|&nbsp;
                <b>Снят:</b> {html_escape(produced)} &nbsp;|&nbsp;
                <b>Файл:</b> HTML из JSON (без пересборки из MCP)
            </div>
        </div>
        <div class="report-indicator">
            <div class="report-indicator-circle" style="background: {gradient};">
                {html_escape(verdict)}
            </div>
        </div>
    </div>
    """


def build_meta_box(snap: dict) -> str:
    meta = snap.get("_meta", {})
    src_gen = snap.get("source_generator", "?")
    src_ver = snap.get("source_generator_version", "?")
    return f"""
    <div class="meta-box">
        <b>Snapshot:</b> {html_escape(meta.get('generator', '?'))} v{html_escape(meta.get('generator_version', '?'))}
        &nbsp;|&nbsp; <b>Schema:</b> {html_escape(meta.get('schema_version', '?'))}
        &nbsp;|&nbsp; <b>Source:</b> {html_escape(src_gen)} v{html_escape(src_ver)}
        &nbsp;|&nbsp; <b>Snapshot kind:</b> {html_escape(meta.get('snapshot_kind', '?'))}
        &nbsp;|&nbsp; <b>Produced:</b> {html_escape(meta.get('produced_at', '?'))}
    </div>
    """


def build_summary_section(snap: dict) -> str:
    sections = snap.get("summary_sections", [])
    if not sections:
        return ""
    rows_html = ""
    for s in sections:
        bg = COLOR_TO_BG.get(s.get("_color", "neutral"), PALETTE["paper"])
        rows_html += f"""
        <tr style="background: {bg};">
            <td style="text-align:center; font-weight:700;">{html_escape(s.get('#', ''))}</td>
            <td>{html_escape(s.get('Цвет', ''))}</td>
            <td><b>{html_escape(s.get('Раздел', ''))}</b></td>
            <td>{html_escape(s.get('Статус', ''))}</td>
            <td>{html_escape(s.get('Детали', ''))}</td>
        </tr>
        """
    return f"""
    <details class="section" open>
        <summary><h2 class="section-title">Сводка по разделам</h2></summary>
        <div class="section-content">
            <table class="tbl">
                <thead><tr>
                    <th>#</th><th>Цвет</th><th>Раздел</th><th>Статус</th><th>Детали</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </details>
    """


def build_section(snap: dict, key: str, title_hint: str = None) -> str:
    sec = snap.get(key)
    if not sec:
        return ""
    title = sec.get("title", title_hint or key)
    rows = sec.get("rows", [])
    status = sec.get("status", "")
    color = sec.get("color", "neutral")
    itog = sec.get("итог", "")
    if not rows:
        return f"""
        <details class="section">
            <summary><h2 class="section-title">{html_escape(title)} — <i>{html_escape(status)}</i></h2></summary>
            <div class="section-content"><p>{html_escape(itog)}</p></div>
        </details>
        """
    headers = list(rows[0].keys())
    headers = [h for h in headers if h != "_color"]
    header_html = "".join(f"<th>{html_escape(h)}</th>" for h in headers)
    body_html = ""
    for r in rows:
        bg = COLOR_TO_BG.get(r.get("_color", "neutral"), PALETTE["paper"])
        cells = "".join(f"<td>{html_escape(r.get(h, ''))}</td>" for h in headers)
        body_html += f'<tr style="background: {bg};">{cells}</tr>'

    return f"""
    <details class="section">
        <summary>
            <h2 class="section-title">{html_escape(title)} — <i>{html_escape(status)}</i>
            {f' <small style="color:{PALETTE["muted"]}; font-weight:400;">({html_escape(itog)})</small>' if itog else ''}
            </h2>
        </summary>
        <div class="section-content">
            <table class="tbl">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{body_html}</tbody>
            </table>
        </div>
    </details>
    """


def render_html(snap: dict) -> str:
    verdict = snap.get("verdict", "Неопределено")
    project_code = snap.get("_meta", {}).get("project_code", "?")
    produced = snap.get("_meta", {}).get("produced_at", "")
    title = f"{project_code} — {verdict} — слепок {produced}"

    body_sections = "".join([
        build_summary_section(snap),
        build_section(snap, "section_3"),
        build_section(snap, "section_4"),
        build_section(snap, "section_5"),
        build_section(snap, "section_6"),
        build_section(snap, "section_7"),
    ])

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{html_escape(title)}</title>
<style>{build_css()}</style>
</head>
<body>
<div class="report-container">
    {build_header(snap)}
    {build_meta_box(snap)}
    {body_sections}
    <div style="text-align: center; margin-top: 24px; font-size: 11px; color: {PALETTE['gray_text']};">
        HTML сгенерирован из JSON-слепка fst-project-health-snapshot (без обращения к MCP).
        Источник: <code>{html_escape(snap.get('_meta', {}).get('produced_at', '?'))}</code>.
    </div>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Генерация HTML из JSON-слепка")
    ap.add_argument("--json", required=True, help="Путь к JSON-файлу")
    ap.add_argument("--output", type=str, default=None, help="Путь к .html")
    args = ap.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ {json_path} не найден")
        sys.exit(1)

    snap = json.loads(json_path.read_text(encoding="utf-8"))
    project_code = snap.get("_meta", {}).get("project_code", "unknown")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.output) if args.output else Path(f"{project_code}_{ts}_from_snapshot.html")
    out_path.write_text(render_html(snap), encoding="utf-8")
    print(f"✅ HTML: {out_path} ({out_path.stat().st_size} байт)")


if __name__ == "__main__":
    main()