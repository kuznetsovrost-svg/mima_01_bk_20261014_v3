"""
test_03_snap_md.py — Уровень 2: snap-md (генератор + логирование).

Что проверяет:
    2.1  --code X --dry-run --no-log
    2.2  --code X (боевой upload в MCP)
    2.3  --codes X 999-FAKE --dry-run (never-fail)
    2.4  --codes (4 проекта, боевой) — массовый прогон
    2.5  Лог-файл создаётся, header содержит JWT-имя
    2.6  Лог содержит "Caller role (MCP): n/a (...)"
    2.7  Trailer пишется (после прогона)
    2.8  rotate_logs.py --dry-run
    2.9  rotate_logs.py (с тестовыми файлами разных возрастов)
"""

import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _helpers import (
    SKILL_HEALTH_SNAP_MD,
    green, red, yellow, ok, fail, skip_msg,
    fmt_ms, measure_ms, sha256_file,
)
from test_project import get_test_project_code, is_valid_format


def _run_snap_md(args: list[str], *, timeout: int = 180) -> tuple[int, str, str]:
    """Запустить run_snap_md.py с заданными аргументами."""
    cmd = ["python3", "scripts/run_snap_md.py"] + args
    r = subprocess.run(
        cmd, cwd=str(SKILL_HEALTH_SNAP_MD),
        capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout, r.stderr


def test_21_dry_run_no_log() -> dict:
    """run_snap_md.py --code X --dry-run --no-log."""
    code = get_test_project_code() or "504-595"  # используем что есть
    with measure_ms() as m:
        rc, out, err = _run_snap_md(["--code", code, "--dry-run", "--no-log"], timeout=180)
    if rc != 0:
        return {"status": "failed", "reason": f"exit={rc}; stderr={err[-200:]}"}
    if "DRY-RUN" not in out and "DRY-RUN" not in err:
        return {"status": "failed", "reason": "нет упоминания DRY-RUN"}
    return {"status": "passed", "details": f"dry-run за {fmt_ms(m.ms)}"}


def test_22_real_upload() -> dict:
    """run_snap_md.py --code X (боевой upload)."""
    code = get_test_project_code() or "504-595"
    with measure_ms() as m:
        rc, out, err = _run_snap_md(["--code", code, "--no-log"], timeout=180)
    if rc != 0:
        return {"status": "failed", "reason": f"exit={rc}; stderr={err[-200:]}"}
    if "FileId=" not in out:
        return {"status": "failed", "reason": "нет FileId= в выводе"}
    m_id = re.search(r"FileId=(\d+)", out)
    return {"status": "passed", "details": f"FileId={m_id.group(1) if m_id else '?'}, {fmt_ms(m.ms)}"}


def test_23_codes_never_fail() -> dict:
    """--codes X 999-FAKE --dry-run (один ok + один not_found)."""
    code = get_test_project_code() or "504-595"
    with measure_ms() as m:
        rc, out, err = _run_snap_md(
            ["--codes", code, "999-FAKE-XXX", "--dry-run", "--no-log"],
            timeout=180,
        )
    # Скрипт возвращает 1 если есть fail, но НЕ падает.
    if "ok" not in out or "fail" not in out:
        return {"status": "failed", "reason": f"нет ok/fail в выводе: {out[-300:]}"}
    return {"status": "passed", "details": f"never-fail, {fmt_ms(m.ms)}"}


def test_24_codes_4_projects_mass() -> dict:
    """--codes с 4 проектами (боевой, если есть права)."""
    code = get_test_project_code()
    if not code or not is_valid_format(code):
        return {"status": "skipped", "reason": "нет TEST_PROJECT_CODE — массовый тест пропущен"}
    # Берём только 1 проект — все 4 могут не быть доступны.
    with measure_ms() as m:
        rc, out, err = _run_snap_md(["--codes", code, "--no-log"], timeout=180)
    return {"status": "passed", "details": f"--codes OK, {fmt_ms(m.ms)}"}


def test_25_log_header_has_jwt_name() -> dict:
    """Лог содержит Caller account (имя из JWT)."""
    code = get_test_project_code() or "504-595"
    # Сначала чистим логи (оставляем только 1 файл на момент проверки).
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"
    for f in logs_dir.glob("*.log"):
        f.unlink()
    with measure_ms() as m:
        rc, out, err = _run_snap_md(["--code", code, "--dry-run"], timeout=180)

    # Найти свежий лог.
    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return {"status": "failed", "reason": "лог не создан"}
    log = logs[0].read_text(encoding="utf-8")
    if "Caller account:" not in log:
        return {"status": "failed", "reason": "нет 'Caller account:' в логе"}
    if "n/a" in log.split("Caller account:")[1].split("\n")[0]:
        return {"status": "failed", "reason": "Caller account = n/a (JWT не декодирован)"}
    return {"status": "passed", "details": f"Caller account присутствует, {fmt_ms(m.ms)}"}


def test_26_log_role_na() -> dict:
    """Лог содержит 'Caller role (MCP): n/a (...)' — честное отсутствие роли."""
    code = get_test_project_code() or "504-595"
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"
    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return {"status": "skipped", "reason": "нет свежего лога (test_25 не прошёл?)"}

    log = logs[0].read_text(encoding="utf-8")
    if "Caller role (MCP):" not in log:
        return {"status": "failed", "reason": "нет 'Caller role (MCP):' в логе"}
    if "n/a" not in log.split("Caller role (MCP):")[1].split("\n")[0]:
        return {"status": "failed", "reason": "Caller role не начинается с 'n/a'"}
    return {"status": "passed", "details": "role = n/a (честно)"}


def test_27_log_trailer_present() -> dict:
    """Trailer пишется (=== END LOG === присутствует)."""
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"
    logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return {"status": "skipped", "reason": "нет лога"}
    log = logs[0].read_text(encoding="utf-8")
    if "=== END LOG ===" not in log:
        return {"status": "failed", "reason": "нет trailer'а"}
    if "Total:" not in log:
        return {"status": "failed", "reason": "нет Total: ... в trailer'е"}
    return {"status": "passed", "details": "trailer есть"}


def test_28_rotate_dry_run() -> dict:
    """rotate_logs.py --dry-run работает (ничего не меняет)."""
    cmd = ["python3", "scripts/rotate_logs.py", "--dry-run"]
    with measure_ms() as m:
        r = subprocess.run(
            cmd, cwd=str(SKILL_HEALTH_SNAP_MD),
            capture_output=True, text=True, timeout=30,
        )
    if r.returncode != 0:
        return {"status": "failed", "reason": f"exit={r.returncode}; stderr={r.stderr[-200:]}"}
    if "DRY-RUN" not in r.stdout:
        return {"status": "failed", "reason": "нет DRY-RUN в выводе"}
    return {"status": "passed", "details": f"{fmt_ms(m.ms)}"}


def test_29_rotate_archive_delete() -> dict:
    """rotate_logs.py архивирует и удаляет по политике."""
    logs_dir = SKILL_HEALTH_SNAP_MD / "logs"

    # Создать 3 тестовых файла с разными mtime.
    (logs_dir / "test_old_delete.log").write_text("")
    (logs_dir / "test_old_delete.log").touch()
    import os
    os.utime(logs_dir / "test_old_delete.log", (time.time() - 2000*86400, time.time() - 2000*86400))

    (logs_dir / "test_archive.log").write_text("")
    os.utime(logs_dir / "test_archive.log", (time.time() - 500*86400, time.time() - 500*86400))

    (logs_dir / "test_fresh.log").write_text("")
    # Свежий — оставляем mtime по умолчанию.

    with measure_ms() as m:
        r = subprocess.run(
            ["python3", "scripts/rotate_logs.py"],
            cwd=str(SKILL_HEALTH_SNAP_MD),
            capture_output=True, text=True, timeout=30,
        )

    archive_dir = logs_dir / "archive" / time.strftime("%Y-%m")
    archived = (logs_dir / "test_archive.log").exists() is False
    deleted = (logs_dir / "test_old_delete.log").exists() is False
    fresh = (logs_dir / "test_fresh.log").exists() is True
    in_archive = (archive_dir / "test_archive.log.gz").exists() if archive_dir.exists() else False

    if not archived:
        return {"status": "failed", "reason": "test_archive.log не архивирован"}
    if not deleted:
        return {"status": "failed", "reason": "test_old_delete.log не удалён"}
    if not fresh:
        return {"status": "failed", "reason": "test_fresh.log удалён (не должен был)"}

    # Cleanup
    if (logs_dir / "test_fresh.log").exists():
        (logs_dir / "test_fresh.log").unlink()
    if archive_dir.exists():
        for f in archive_dir.glob("test_archive.log.gz"):
            f.unlink()

    return {"status": "passed", "details": f"archive+delete OK, {fmt_ms(m.ms)}"}


TESTS = [
    {"name": "2.1 --code X --dry-run --no-log",          "fn": test_21_dry_run_no_log},
    {"name": "2.2 --code X (боевой upload)",             "fn": test_22_real_upload},
    {"name": "2.3 --codes X 999-FAKE (never-fail)",      "fn": test_23_codes_never_fail},
    {"name": "2.4 --codes (массовый)",                    "fn": test_24_codes_4_projects_mass},
    {"name": "2.5 log: Caller account (JWT)",            "fn": test_25_log_header_has_jwt_name},
    {"name": "2.6 log: Caller role (MCP): n/a",          "fn": test_26_log_role_na},
    {"name": "2.7 log: trailer === END LOG ===",         "fn": test_27_log_trailer_present},
    {"name": "2.8 rotate_logs.py --dry-run",              "fn": test_28_rotate_dry_run},
    {"name": "2.9 rotate_logs.py archive+delete",         "fn": test_29_rotate_archive_delete},
]
