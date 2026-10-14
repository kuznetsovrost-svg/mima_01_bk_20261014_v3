#!/usr/bin/env python3
"""
run.py — convenience: извлечь MD из MCP → собрать HTML.

Это просто обёртка над двумя предыдущими:
  1) fetch_snapshot.py с заданным режимом → кладёт MD в кэш
  2) build_html.py <cache_md> → собирает HTML

v1.0.19: never-fail. Лог пишется по тем же правилам.

Использование:
    python3 run.py --code 504-595 --last
    python3 run.py --codes 504-595 503-152 --at "2026-09-23"
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from logging_utils import RunLogger, decode_jwt_user

SKILL_VERSION = "1.0.19"
SCRIPT_DIR = Path(__file__).resolve().parent


def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch + Build HTML из MD-снимка в карточке проекта.")
    ap.add_argument("--code", type=str, default=None)
    ap.add_argument("--codes", nargs="+", default=None)
    # Режим выбора (как в fetch_snapshot.py):
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--nearest", action="store_true", help="(default) Ближайший к --at.")
    mode.add_argument("--exact", type=str, default=None)
    mode.add_argument("--last", action="store_true", help="Самый свежий.")
    mode.add_argument("--first", action="store_true", help="Самый ранний.")
    mode.add_argument("--pick", action="store_true", help="Интерактивный выбор.")
    mode.add_argument("--list", action="store_true", help="Только список (--html=false).")
    ap.add_argument("--at", type=str, default=None, help="Точка во времени для --nearest.")
    ap.add_argument("--html", action="store_true", default=True,
                    help="Собирать HTML после извлечения (по умолчанию).")
    ap.add_argument("--no-html", dest="html", action="store_false",
                    help="Только извлечь MD, без HTML.")
    ap.add_argument("--no-log", action="store_true", help="Не писать лог.")
    args = ap.parse_args()

    if args.code and args.codes:
        ap.error("--code и --codes — взаимоисключающие")
    if args.code:
        projects = [args.code]
    elif args.codes:
        projects = list(args.codes)
    else:
        ap.error("Укажите --code X или --codes X Y Z")

    # Шаг 1: fetch
    fetch_cmd = [sys.executable, str(SCRIPT_DIR / "fetch_snapshot.py")]
    if args.codes:
        fetch_cmd += ["--codes"] + projects
    else:
        fetch_cmd += ["--code"] + projects
    if args.last:
        fetch_cmd.append("--last")
    elif args.first:
        fetch_cmd.append("--first")
    elif args.pick:
        fetch_cmd.append("--pick")
    elif args.exact:
        fetch_cmd.extend(["--exact", args.exact])
    elif args.at:
        fetch_cmd.extend(["--nearest", "--at", args.at])
    elif args.list:
        fetch_cmd.append("--list")

    if args.no_log:
        fetch_cmd.append("--no-log")

    print(bold(f"\n📦 fst-project-health-from-md-snapshot v{SKILL_VERSION} (run)"))
    print(f"   Step 1: {' '.join(fetch_cmd[1:])}")
    fetch_proc = subprocess.run(fetch_cmd, capture_output=True, text=True)

    if fetch_proc.returncode != 0 and not args.list:
        print(red(f"fetch вернул код {fetch_proc.returncode}"))
        print(fetch_proc.stdout[-300:])
        print(red(fetch_proc.stderr[-300:]))
        return fetch_proc.returncode
    print(fetch_proc.stdout)
    if args.list:
        return 0

    # Шаг 2: HTML (если включён).
    if not args.html:
        return 0

    # Найдём свежескачанные MD в кэше.
    cache_dir = Path.home() / ".hermes/profiles/fst-control/cache/snapshots"
    if not cache_dir.exists():
        print(red("Кэш пуст — нечего собирать в HTML"))
        return 1

    # Берём последний файл для каждого проекта (после только что сделанного fetch).
    just_now_prefix = datetime.now().strftime("%Y-%m-%d")
    html_count = 0
    for code in projects:
        candidates = sorted(cache_dir.glob(f"{code}_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print(yellow(f"  ⚠ {code}: нет свежего MD в кэше — HTML не собран"))
            continue
        md = candidates[0]
        # Шаг 2.
        html_cmd = [sys.executable, str(SCRIPT_DIR / "build_html.py"), "--md", str(md)]
        if args.no_log:
            html_cmd.append("--no-log")
        print(f"\n   Step 2 ({code}): {' '.join(html_cmd[1:])}")
        html_proc = subprocess.run(html_cmd, capture_output=True, text=True)
        if html_proc.returncode == 0:
            print(green(f"  ✓ {code}: HTML собран"))
            html_count += 1
        else:
            print(red(f"  ✗ {code}: HTML FAIL ({html_proc.returncode})"))
            print(html_proc.stdout[-200:])
            print(red(html_proc.stderr[-200:]))

    print(bold(f"\n{'='*60}"))
    print(bold(f"ИТОГ: HTML собран по {html_count}/{len(projects)} проектам"))
    print(bold(f"{'='*60}"))

    return 0 if html_count == len(projects) else 1


if __name__ == "__main__":
    sys.exit(main())
