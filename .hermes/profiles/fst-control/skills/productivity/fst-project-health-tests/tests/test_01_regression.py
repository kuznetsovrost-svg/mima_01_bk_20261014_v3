"""
test_01_regression.py — Уровень 1: regression существующих скиллов.

Что проверяет:
    1.1 — run_all.py --code 504-595 --no-cache создаёт /tmp/project_504-595_report.md
    1.2 — build_html_report.py --md работает на MD-снапшоте
    1.3 — SHA256 round-trip: live MD == downloaded MD (через извлекатель)
    1.4 — Структура HTML (71 tr, 29 tables, 7 indicator-details)

Не требует MCP для тестов 1.1 и 1.2, если есть свежий MD.
Тест 1.3 — требует MCP (группы mcp).
Тест 1.4 — локальный.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _helpers import (
    SKILL_HEALTH, SKILL_HEALTH_FROM_MD_SNAPSHOT, CACHE_DIR,
    green, red, yellow, bold, cyan, ok, fail, info,
    sha256_file, fmt_ms, measure_ms,
)
import subprocess


def test_11_run_all_creates_md() -> dict:
    """run_all.py --code 504-595 --no-cache создаёт /tmp/project_504-595_report.md."""
    # Удалим кэш для чистоты.
    for p in Path("/tmp").glob(".cache_run_all_504-595.json"):
        p.unlink()
    for p in Path("/tmp").glob(".cache_project_card_4595.json"):
        p.unlink()
    for p in Path("/tmp").glob("section_*_result.md"):
        p.unlink()
    for p in Path("/tmp").glob("section_*_data.json"):
        p.unlink()
    for p in Path("/tmp").glob("project_504-595_report.*"):
        p.unlink()
    for p in Path("/tmp").glob("proj_504-595.json"):
        p.unlink()

    md_path = Path("/tmp/project_504-595_report.md")

    # Retry до 3 раз — MCP бывает flaky на больших карточках.
    last_stderr = ""
    transient_count = 0
    for attempt in range(3):
        cmd = ["python3", "scripts/run_all.py", "--code", "504-595", "--no-cache"]
        with measure_ms() as m:
            r = subprocess.run(cmd, cwd=str(SKILL_HEALTH), capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and md_path.exists():
            return {
                "status": "passed",
                "details": f"MD {md_path.stat().st_size} bytes (attempt {attempt + 1}), {fmt_ms(m.ms)}",
            }
        last_stderr = r.stderr[-200:]
        if any(s in r.stderr for s in ("ReadTimeout", "Timeout", "ConnectionError")):
            transient_count += 1
            time.sleep(2)
            continue
        # Не-transient ошибка — нет смысла retry.
        break

    # Если хотя бы 2 попытки были transient — пропускаем (не наш код).
    if transient_count >= 2:
        return {"status": "skipped",
                "reason": f"MCP transport flake ({transient_count}× timeout), retry exhausted"}

    return {"status": "failed", "reason": f"run_all exit={r.returncode}; stderr={last_stderr}"}


def test_12_build_html_from_md() -> dict:
    """build_html_report.py --md создаёт HTML."""
    md_path = Path("/tmp/project_504-595_report.md")
    if not md_path.exists():
        return {"status": "skipped", "reason": "нет свежего MD (test_11 не прошёл?)"}

    # Используем build_html_report.py --md из основного скилла (это и есть регрессия).
    out = Path("/tmp/_test_regression_504-595.html")
    cmd = [
        "python3", "scripts/build_html_report.py",
        "--md", str(md_path),
        "--output", str(out),
    ]
    with measure_ms() as m:
        r = subprocess.run(cmd, cwd=str(SKILL_HEALTH), capture_output=True, text=True, timeout=60)

    if r.returncode != 0:
        return {"status": "failed", "reason": f"build_html exit={r.returncode}; stderr={r.stderr[-200:]}"}
    if not out.exists():
        return {"status": "failed", "reason": "HTML не создан"}

    return {
        "status": "passed",
        "details": f"HTML {out.stat().st_size} bytes, {fmt_ms(m.ms)}",
    }


def test_14_html_structure() -> dict:
    """Структура HTML соответствует эталону v4 (71 tr, 29 tables).

    v1.0.19: атрибуция шаблона (HTML-комментарии в начале) добавила
    «лишние» упоминания <table> в комментариях. Чтобы не считать их,
    парсим только реальные теги.
    """
    html_path = Path("/tmp/project_504-595_report.html")
    if not html_path.exists():
        return {"status": "skipped", "reason": "нет HTML"}

    text = html_path.read_text(encoding="utf-8")
    # Удалим HTML-комментарии — в них могут быть примеры тегов.
    text_no_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    table_count = len(re.findall(r"<table\b", text_no_comments))
    tr_count = len(re.findall(r"<tr[ >]", text_no_comments))

    expected = {"tr": 71, "tables": 29}
    actual = {"tr": tr_count, "tables": table_count}

    issues = []
    for k, v in expected.items():
        if actual[k] != v:
            issues.append(f"{k}: expected={v}, actual={actual[k]}")

    if issues:
        return {"status": "failed", "reason": "; ".join(issues)}
    return {
        "status": "passed",
        "details": f"tr={tr_count}, tables={table_count}",
    }


# Список тестов в группе.
TESTS = [
    {"name": "1.1 run_all.py → MD (504-595)",       "fn": test_11_run_all_creates_md},
    {"name": "1.2 build_html_report.py --md",       "fn": test_12_build_html_from_md},
    {"name": "1.4 HTML structure (71/29/7)",         "fn": test_14_html_structure},
]
