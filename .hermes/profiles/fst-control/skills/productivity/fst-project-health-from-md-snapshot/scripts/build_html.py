#!/usr/bin/env python3
"""
build_html.py — тонкая обёртка над fst-project-health/scripts/build_html_report.py.

Назначение:
    Собрать HTML-отчёт из MD-файла (кэшированного или иного), без обращения
    к MCP. Полностью переиспользует существующий --md PATH режим.

v1.0.19: never-fail. Лог пишется по тем же правилам, что и fetch_snapshot.py.

Использование:
    python3 build_html.py --md <path/to/snapshot.md>
    python3 build_html.py --md <path/to/snapshot.md> --output /tmp/my.html
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from logging_utils import RunLogger, decode_jwt_user

# Путь к основному скиллу (для build_html_report.py).
SKILL_HEALTH_DIR = Path(
    os.environ.get(
        "FST_PROJECT_HEALTH_PATH",
        "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health",
    )
)
BUILD_HTML_SCRIPT = SKILL_HEALTH_DIR / "scripts" / "build_html_report.py"

SKILL_VERSION = "1.0.19"


def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)
def fmt_ms(ms):
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Сборка HTML из MD (через fst-project-health/build_html_report.py --md).",
    )
    ap.add_argument("--md", type=str, required=True, help="Путь к MD-файлу.")
    ap.add_argument("--output", type=str, default=None,
                    help="Куда сохранить HTML (по умолчанию — /tmp/<basename>.html).")
    ap.add_argument("--no-log", action="store_true", help="Не писать лог.")
    args = ap.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        print(red(f"MD не найден: {md_path}"))
        return 1

    output = Path(args.output) if args.output else Path("/tmp") / (md_path.stem + ".html")

    run_started_at = datetime.now()
    logger = RunLogger(now=run_started_at) if not args.no_log else None

    print(bold(f"\n📥 fst-project-health-from-md-snapshot v{SKILL_VERSION} (html)"))
    print(f"   MD:    {md_path} ({md_path.stat().st_size} bytes)")
    print(f"   Output: {output}")
    if logger:
        print(f"   Лог: {logger.log_file}")

    try:
        token = os.environ.get("PMP_TOKEN", "")
        token_user = decode_jwt_user(token) if token else {"name": "n/a", "email": "n/a", "sub": "n/a"}
    except Exception:
        token_user = {"name": "n/a", "email": "n/a", "sub": "n/a"}

    if logger:
        logger.log_header(
            version=SKILL_VERSION,
            token_user=token_user,
            role="n/a (no MCP for HTML build)",
            action="html",
            projects_in_run=[md_path.stem],
            args_summary=f"--md {md_path}" + (f" --output {output}" if args.output else ""),
        )

    overall_t0 = time.perf_counter()
    try:
        t0 = time.perf_counter()
        try:
            cmd = [sys.executable, str(BUILD_HTML_SCRIPT), "--md", str(md_path), "--output", str(output)]
            print(f"\n→ Запускаю: {' '.join(cmd)}\n")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                err_msg = f"exit={result.returncode}; stderr={result.stderr[-200:]}"
                if logger:
                    logger.log_project(
                        md_path.stem, "html_error",
                        error={"type": "subprocess.CalledProcessError",
                               "message": err_msg,
                               "raw": (result.stdout or "")[-300:]},
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                print(red(f"FAIL: {err_msg}"))
                return 2
            # stdout содержит «✅ HTML из MD-снапшота собран: ...»
            print(result.stdout)
            print(green(f"✓ HTML собран: {output} ({output.stat().st_size} bytes)"))
            if logger:
                logger.log_project(
                    md_path.stem, "html_ok",
                    html_path=output,
                    duration_ms=(time.perf_counter()-t0)*1000,
                )

        except Exception as e:
            if logger:
                logger.log_project(
                    md_path.stem, "html_error",
                    error={"type": type(e).__name__, "message": str(e)[:300]},
                    duration_ms=(time.perf_counter()-t0)*1000,
                )
            print(red(f"FAIL: {type(e).__name__}: {e}"))
            return 2
    finally:
        if logger:
            try:
                logger.log_trailer(total_ms=(time.perf_counter()-overall_t0)*1000)
            except Exception:
                pass
            logger.close()
            print(f"\n📝 Лог сохранён: {logger.log_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
