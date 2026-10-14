"""
test_06_invariants.py — Уровень 6: 4 инварианта устойчивости.

Инвариант 1: Никогда не падать на середине цикла. Каждый проект в try/except + continue.
Инвариант 2: Полнота ошибки в логе: type, message, http_code, raw[:300].
Инвариант 3: Header раньше body. Дата, аккаунт, роль, список проектов — ДО первого проекта.
Инвариант 4: Список проектов — snapshot. Сохраняется в копию (list(DEFAULT_PROJECTS)).

Что проверяет:
    6.1  В run_snap_md.py каждый проект в try/except (статический анализ кода).
    6.2  В fetch_snapshot.py каждый проект в try/except (статический анализ).
    6.3  Лог содержит type:, message: на ошибке.
    6.4  В логе header пишется ДО первого проекта (структурный тест).
    6.5  DEFAULT_PROJECTS сохраняется в копию (list()).
    6.6  trailer пишется в finally: (статический анализ).
"""

import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _helpers import (
    SKILL_HEALTH_SNAP_MD, SKILL_HEALTH_FROM_MD_SNAPSHOT,
    fmt_ms, measure_ms, ok, fail,
)
from test_project import get_test_project_code, is_valid_format


# 6.1 — статический анализ run_snap_md.py
def test_61_snap_md_try_except_per_project() -> dict:
    """В run_snap_md.py каждый проект в try/except + continue."""
    src = (SKILL_HEALTH_SNAP_MD / "scripts" / "run_snap_md.py").read_text(encoding="utf-8")
    # В цикле for code in projects_in_run должны быть try + except + continue.
    has_try = "for code in" in src and "try:" in src.split("for code in", 1)[1]
    has_except = "except Exception" in src.split("for code in", 1)[1]
    has_continue = "continue" in src.split("for code in", 1)[1]
    if not (has_try and has_except and has_continue):
        return {"status": "failed",
                "reason": f"try={has_try}, except={has_except}, continue={has_continue}"}
    return {"status": "passed", "details": "try/except/continue в цикле"}


# 6.2 — то же для fetch_snapshot.py
def test_62_fetch_try_except_per_project() -> dict:
    """В fetch_snapshot.py каждый проект в try/except + continue."""
    src = (SKILL_HEALTH_FROM_MD_SNAPSHOT / "scripts" / "fetch_snapshot.py").read_text(encoding="utf-8")
    after_loop = src.split("for code in", 1)[1] if "for code in" in src else ""
    has_try = "try:" in after_loop
    has_except = "except Exception" in after_loop
    has_continue = "continue" in after_loop
    if not (has_try and has_except and has_continue):
        return {"status": "failed",
                "reason": f"try={has_try}, except={has_except}, continue={has_continue}"}
    return {"status": "passed", "details": "try/except/continue в цикле"}


# 6.3 — лог содержит type:, message: на ошибке
def test_63_log_error_fields_complete() -> dict:
    """При ошибке лог содержит type:, message:, http_code (если есть)."""
    code = get_test_project_code() or "504-595"
    # Запустим --codes с заведомо неверным вторым кодом.
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"
    for f in logs_dir.glob("*.log"):
        f.unlink()

    r = subprocess.run(
        ["python3", "scripts/run_snap_md.py", "--codes", code, "999-FAKE-XXX", "--dry-run"],
        cwd=str(SKILL_HEALTH_SNAP_MD),
        capture_output=True, text=True, timeout=180,
    )

    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return {"status": "failed", "reason": "лог не создан"}
    log = logs[0].read_text(encoding="utf-8")

    if "type:" not in log:
        return {"status": "failed", "reason": "нет 'type:' в логе"}
    if "message:" not in log:
        return {"status": "failed", "reason": "нет 'message:' в логе"}
    return {"status": "passed", "details": "type+message присутствуют"}


# 6.4 — header пишется ДО первого проекта
def test_64_header_before_body() -> dict:
    """В логе header пишется до первого упоминания проекта."""
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"
    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return {"status": "skipped", "reason": "нет лога"}
    log = logs[0].read_text(encoding="utf-8")

    # Найти позицию 'Projects in run:' (в header) и '✓ ' или '✗ ' (в body).
    header_pos = log.find("Projects in run:")
    body_pos = log.find("\n  ✓")
    if body_pos == -1:
        body_pos = log.find("\n  ✗")
    if header_pos == -1 or body_pos == -1:
        return {"status": "failed", "reason": f"header_pos={header_pos}, body_pos={body_pos}"}
    if header_pos >= body_pos:
        return {"status": "failed", "reason": f"header пишется ПОСЛЕ body ({header_pos} vs {body_pos})"}
    return {"status": "passed", "details": f"header@{header_pos}, body@{body_pos}"}


# 6.5 — DEFAULT_PROJECTS сохраняется в копию
def test_65_projects_snapshot_copy() -> dict:
    """DEFAULT_PROJECTS копируется через list() в main()."""
    src = (SKILL_HEALTH_SNAP_MD / "scripts" / "run_snap_md.py").read_text(encoding="utf-8")
    # Должно быть: projects_in_script = list(DEFAULT_PROJECTS)
    if "projects_in_script = list(DEFAULT_PROJECTS)" not in src:
        return {"status": "failed", "reason": "нет 'projects_in_script = list(DEFAULT_PROJECTS)'"}
    return {"status": "passed", "details": "DEFAULT_PROJECTS копируется"}


# 6.6 — trailer пишется в finally:
def test_66_finally_trailer() -> dict:
    """log_trailer пишется в finally: блоке."""
    src = (SKILL_HEALTH_SNAP_MD / "scripts" / "run_snap_md.py").read_text(encoding="utf-8")
    # Должен быть finally: блок с logger.log_trailer.
    if "finally:" not in src:
        return {"status": "failed", "reason": "нет finally: блока"}
    if "logger.log_trailer" not in src:
        return {"status": "failed", "reason": "нет logger.log_trailer"}
    # Проверим, что log_trailer находится внутри finally.
    finally_idx = src.rfind("finally:")
    after_finally = src[finally_idx:]
    if "log_trailer" not in after_finally:
        return {"status": "failed", "reason": "log_trailer не внутри finally"}
    return {"status": "passed", "details": "trailer в finally"}


TESTS = [
    {"name": "6.1 snap-md: try/except/continue",          "fn": test_61_snap_md_try_except_per_project},
    {"name": "6.2 fetch: try/except/continue",            "fn": test_62_fetch_try_except_per_project},
    {"name": "6.3 log: type, message на ошибке",          "fn": test_63_log_error_fields_complete},
    {"name": "6.4 log: header до body",                   "fn": test_64_header_before_body},
    {"name": "6.5 DEFAULT_PROJECTS = list(...)",          "fn": test_65_projects_snapshot_copy},
    {"name": "6.6 trailer в finally:",                    "fn": test_66_finally_trailer},
]
